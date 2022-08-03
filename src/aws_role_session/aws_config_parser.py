# pylint: disable=missing-function-docstring
import os
from configparser import ConfigParser
from datetime import datetime, timezone

DEFAULT_REGION = "eu-west-1"


class AwsConfigParser(ConfigParser):
    def __init__(self, profile_name, default_region=None):
        super().__init__()
        self._read_config()
        # self._profile_name is the local variable holding the profile name String
        # self.profile_name is the class property that validates the new profile
        self._profile_name = None
        self.profile_name = profile_name
        self._default_region = default_region

    @property
    def profile_name(self):
        return self.profile.name

    @profile_name.setter
    def profile_name(self, value):
        # The handling of section names in ConfigParser appears to be case insensitive
        if value is None:
            raise ValueError(
                "Profile can not be None. It must be configured in the role_session.toml "
                "file, or explicitly when the RoleSession class is initialized."
            )
        self._profile_name = value
        # This will generate an exception in case the profile does not exist
        _ = self.profile.name

    @property
    def temp_profile_name(self):
        return f"temp-{self.profile_name}"

    @property
    def aws_region(self):
        return (
            region
            if (region := self.profile.get("aws_region", None)) is not None
            else self._default_region
        )

    @property
    def _credentials_file(self):
        # The AWS credentials file is expected to be in the default location
        # The actual path depends on the platform
        filename = os.path.join(os.path.expanduser("~"), ".aws", "credentials")
        if not os.path.exists(filename):
            raise RuntimeError(f"AWS Credentials file {filename} does not exist")
        return filename

    @property
    def profile(self):
        return self._read_profile(
            profile_name=self._profile_name,
            allow_missing_profile=False,
        )

    @property
    def temp_profile(self):
        return self._read_profile(
            profile_name=self.temp_profile_name,
            allow_missing_profile=True,
        )

    @property
    def profile_access_key_id(self):
        return self._get_setting(self.profile, "aws_access_key_id")

    @property
    def profile_secret_access_key(self):
        return self._get_setting(self.profile, "aws_secret_access_key")

    @property
    def profile_mfa_serial(self):
        return self._get_setting(self.profile, "mfa_serial")

    @property
    def profile_mfa_key(self):
        return self._get_setting(self.profile, "mfa_key")

    @property
    def temp_profile_access_key_id(self):
        return self._get_setting(self.temp_profile, "aws_access_key_id")

    @property
    def temp_profile_secret_access_key(self):
        return self._get_setting(self.temp_profile, "aws_secret_access_key")

    @property
    def temp_profile_session_token(self):
        return self._get_setting(self.temp_profile, "aws_session_token")

    @property
    def temp_profile_expiration(self):
        expiration_date = self._get_setting(self.temp_profile, "expiration_utc")
        return (
            datetime.fromisoformat(expiration_date)
            if expiration_date is not None
            else None
        )

    @property
    def temp_profile_is_valid(self):
        return (
            self.temp_profile_expiration >= datetime.now(timezone.utc)
            if self.temp_profile_expiration is not None
            else False
        )

    def _read_config(self):
        self.read(self._credentials_file)
        if not self.sections():
            raise RuntimeError(
                f"AWS Credentials File {self._credentials_file} does not contain any sections"
            )

    def _read_profile(self, profile_name, allow_missing_profile):
        result = self[profile_name] if self.has_section(profile_name) else None
        if result is None and not allow_missing_profile:
            raise RuntimeError(
                f"AWS Credentials file {self._credentials_file} "
                f"does not contain profile {profile_name}"
            )
        return result

    @staticmethod
    def _get_setting(profile, setting_name):
        return profile.get(setting_name, None) if profile is not None else None

    def store_temp_profile(
        self,
        AccessKeyId,
        SecretAccessKey,
        SessionToken,
        Expiration,
    ):
        # Allow arguments to not conform to snake_case naming style
        # This method is designed to directly accept the Credentials section from the STS
        # get_session_token response, which is in snake case
        # pylint: disable=invalid-name
        if self.temp_profile is None:
            self.add_section(self.temp_profile_name)
        self.temp_profile["aws_access_key_id"] = AccessKeyId
        self.temp_profile["aws_secret_access_key"] = SecretAccessKey
        self.temp_profile["aws_session_token"] = SessionToken
        self.temp_profile["expiration_utc"] = str(Expiration)
        with open(
            file=self._credentials_file, mode="wt", encoding="UTF-8"
        ) as configfile:
            self.write(configfile)
