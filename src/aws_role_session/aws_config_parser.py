import os
from configparser import ConfigParser, SectionProxy
from datetime import datetime, timezone
from typing import Any, Optional, Union

DEFAULT_REGION = "eu-west-1"


class AwsConfigParser(ConfigParser):
    """
    Class for easy interaction with the AWS credentials file.

    The class is initializes with a base profile name which is expected in the
    credentials file. This profile gives access to an IAM account and should at
    least provide a valid access key and a secret key. The class supports
    authentication using MFA, which is strongly recommended.

    Based on the base profile, an authenticated session is created and the
    session credentials are stored in a temporary profile in the credentials file.

        - Read the configuration settings for the base profile and provide them
          as class properties for programmatic access
        - Read the configuration settings for the temporary profile (if
          available in the credentials file) and provide them as class
          properties for programmatic access
        - A temporary profile that is expired is considered to not exist
        - Store a new temporary profile (credentials need to be provided)
    """

    def __init__(self, profile_name: str, default_region: Optional[str] = None) -> None:
        super().__init__()
        self._read_config()
        # self._profile_name is the local variable holding the profile name String
        # self.profile_name is the class property that validates the new profile
        self._profile_name = ""
        self.profile_name = profile_name
        self._default_region = default_region

    @property
    def profile_name(self) -> str:
        """The name of the base profile in the credentials file that is used for initial authentication"""
        return self.profile.name

    @profile_name.setter
    def profile_name(self, value: str) -> None:
        # The handling of section names in ConfigParser appears to be case insensitive
        if value is None:
            raise ValueError(
                "Profile can not be None. It must be configured in the "
                "aws_role_session.toml file, or explicitly when the RoleSession "
                "class is initialized."
            )
        self._profile_name = value
        # This will generate an exception in case the profile does not exist
        _ = self.profile.name

    @property
    def temp_profile_name(self) -> str:
        """
        The name of the temporary profile in the credentials file, which is used
        to store the credentials for an authenticated session based on the base
        profile (profile_name). The name is based on the profile_name. If it
        does not yet exist in the credentials file it will be created as soon as
        an authenticated session is opened.
        """
        return f"temp-{self.profile_name}"

    @property
    def aws_region(self) -> Union[str, None]:
        """
        The AWS region to be used for all sessions.
        The region should preferably be configured in the 'default' section in the
        AWS credentials file. Alternatively, it can be configured in the base profile,
        or passed as a variable when the AwsConfigParser class is initialized.
        """
        return (
            region
            if (region := self.profile.get("aws_region", None)) is not None
            else self._default_region
        )

    @property
    def _credentials_file(self) -> str:
        # The AWS credentials file is expected to be in the default location
        # The actual path depends on the platform
        filename = os.path.join(os.path.expanduser("~"), ".aws", "credentials")
        if not os.path.exists(filename):
            raise RuntimeError(f"AWS Credentials file {filename} does not exist")
        return filename

    @property
    def profile(self) -> Union(SectionProxy, None):
        """The base profile that has been read from the credentials file."""
        return self._read_profile(
            profile_name=self._profile_name,
            allow_missing_profile=False,
        )

    @property
    def temp_profile(self) -> Union(SectionProxy, None):
        """
        The temporary profile as read from the credentials file. Returns
        None if the temporary profile does not exist or is expired.
        """
        return self._read_profile(
            profile_name=self.temp_profile_name,
            allow_missing_profile=True,
        )

    @property
    def profile_access_key_id(self) -> Union[str, None]:
        """The aws_access_key_id from the base profile"""
        return self._get_setting(self.profile, "aws_access_key_id")

    @property
    def profile_secret_access_key(self) -> Union[str, None]:
        """The aws_secret_access_key from the base profile"""
        return self._get_setting(self.profile, "aws_secret_access_key")

    @property
    def profile_mfa_serial(self) -> Union[str, None]:
        """The mfa_serial from the base profile"""
        return self._get_setting(self.profile, "mfa_serial")

    @property
    def profile_mfa_key(self) -> Union[str, None]:
        """The mfa_key from the base profile"""
        return self._get_setting(self.profile, "mfa_key")

    @property
    def profile_mfa_is_configured(self) -> bool:
        """
        Indication (boolean) whether MFA is configured in the base profile.
        This is defined by the presence of the settings mfa_key and mfa_serial.
        """
        return self.profile_mfa_key is not None and self.profile_mfa_serial is not None

    @property
    def valid_temp_profile_exists(self) -> bool:
        return self.temp_profile is not None

    @property
    def temp_profile_access_key_id(self) -> Union[str, None]:
        """The aws_access_key_id from the temporary profile"""
        return self._get_setting(self.temp_profile, "aws_access_key_id")

    @property
    def temp_profile_secret_access_key(self) -> Union[str, None]:
        return self._get_setting(self.temp_profile, "aws_secret_access_key")

    @property
    def temp_profile_session_token(self) -> Union[str, None]:
        return self._get_setting(self.temp_profile, "aws_session_token")

    @property
    def temp_profile_expiration(self) -> Union[datetime, None]:
        expiration_date = self._get_setting(self.temp_profile, "expiration_utc")
        return (
            datetime.fromisoformat(expiration_date)
            if expiration_date is not None
            else None
        )

    @staticmethod
    def _is_expired(date_string_utc: str) -> bool:
        datetime_utc = (
            datetime.fromisoformat(date_string_utc)
            if date_string_utc is not None
            else None
        )
        return (
            datetime_utc < datetime.now(timezone.utc)
            if datetime_utc is not None
            else True
        )

    def _read_config(self) -> None:
        self.read(self._credentials_file)
        if not self.sections():
            raise RuntimeError(
                f"AWS Credentials File {self._credentials_file} does not contain any sections"
            )

    def _read_profile(
        self, profile_name: str, allow_missing_profile: bool
    ) -> Union[SectionProxy, None]:
        """
        Return the profile section from the configuration.
        If the profile does not exist:
            - If allow_missing_profile is True: return None.
            - If allow_missing_profile is False: raise a RuntimeError exception.
        If the profile exists:
            - If an expiration date exists in the profile (expiration_utc) and
              is in the past: return None
            - If an expiration date does not exist in the profile, or if an
              expiration date exists and is in the future: return the profile
        """
        profile = None
        if self.has_section(profile_name):
            profile = (
                None
                if "expiration_utc" in (section := self[profile_name]).keys()
                and self._is_expired(section.get("expiration_utc"))
                else section
            )
        if profile is None and not allow_missing_profile:
            raise RuntimeError(
                f"AWS Credentials file {self._credentials_file} "
                f"does not contain profile {profile_name}"
            )
        return profile

    @staticmethod
    def _get_setting(
        profile: SectionProxy, setting_name: str
    ) -> Union[str, bool, None]:
        return profile.get(setting_name, None) if profile is not None else None

    def store_temp_profile(
        self,
        AccessKeyId: str,
        SecretAccessKey: str,
        SessionToken: str,
        Expiration: datetime,
    ) -> None:
        # Allow arguments to not conform to snake_case naming style
        # This method is designed to directly accept the Credentials section from the STS
        # get_session_token response, which is in snake case
        # pylint: disable=invalid-name
        if self.temp_profile is None:
            self.add_section(self.temp_profile_name)
        self.temp_profile["aws_access_key_id"] = AccessKeyId
        self.temp_profile["aws_secret_access_key"] = SecretAccessKey
        self.temp_profile["aws_session_token"] = SessionToken
        self.temp_profile["expiration_utc"] = datetime.isoformat(Expiration)
        with open(
            file=self._credentials_file, mode="wt", encoding="UTF-8"
        ) as configfile:
            self.write(configfile)
