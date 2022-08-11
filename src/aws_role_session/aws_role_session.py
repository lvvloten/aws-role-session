from typing import Optional

import boto3
import pyotp
from botocore.config import Config

from .aws_config_parser import AwsConfigParser
from .aws_role_session_config import AwsRoleSessionConfig


class AwsRoleSession:
    def __init__(
        self,
        profile_name: Optional[str] = None,
        role_name: Optional[str] = None,
        use_mfa: Optional[bool] = None,
        configuration: Optional[dict] = None,
    ) -> None:
        self._config = AwsRoleSessionConfig(configuration)
        self._role_name = (
            role_name if role_name is not None else self._config.default_role
        )
        profile = (
            profile_name if profile_name is not None else self._config.default_profile
        )
        self._aws_config_parser = AwsConfigParser(profile)
        self._use_mfa = use_mfa if use_mfa is not None else self._config.default_use_mfa
        self._sts_client_object = None
        self._role_session_object = None
        self._role_session_account = None

    @property
    def _retry_config(self) -> Config:
        return Config(
            retries={
                "max_attempts": self._config.max_retry_attempts,
                "mode": "standard",
            }
        )

    def get_client(self, account_name: str, service_name: str) -> boto3.client:
        """
        Obtain a client for a given service in the given account
        """
        return self._role_session(account_name).client(
            service_name=service_name,
            config=self._retry_config,
        )

    def get_resource(self, account_name: str, service_name: str) -> boto3.resource:
        """
        Obtain a resource for a given service in the given account
        """
        return self._role_session(account_name).resource(
            service_name=service_name,
            config=self._retry_config,
        )

    @property
    def _sts_client(self) -> boto3.client:
        """
        The authenticated STS client, based on the temporary profile (i.e. the
        authenticated session). This client is used to assume remote roles.
        """
        # We want to create a new STS client if it does not exist, but also if the
        # underlying temporary profile has expired after the client was created
        if (
            self._sts_client_object is None
            or self._aws_config_parser.temp_profile is None
        ):
            self.update_temp_profile()
            self._sts_client_object = boto3.client(
                service_name="sts",
                aws_access_key_id=self._aws_config_parser.temp_profile_access_key_id,
                aws_secret_access_key=self._aws_config_parser.temp_profile_secret_access_key,
                aws_session_token=self._aws_config_parser.temp_profile_session_token,
                region_name=self._aws_config_parser.aws_region,
            )
        return self._sts_client_object

    def _role_session(self, account_name: str) -> boto3.Session:
        """
        _role_session is the boto3 Session object that represents the assumed
        role in the given account
        """
        # There is no way to derive from the Session object to which account it
        # is connected. To avoid that a new session is created unnecessarily,
        # for example when multiple clients or resources are created in the
        # same account, the account name is stored in a separate variable
        if (
            self._role_session_object is None
            or self._role_session_account != account_name
        ):
            self._role_session_object = self._get_role_session(account_name)
            self._role_session_account = account_name
        return self._role_session_object

    def _otp(self) -> str:
        """
        Provides the MFA One Time Password (OTP). If MFA is configured in the
        base profile, the OTP will be generated automatically. Otherwise, the
        user is asked to enter the OTP manually.
        """
        return (
            pyotp.TOTP(self._aws_config_parser.profile_mfa_key).now()
            if self._aws_config_parser.profile_mfa_is_configured
            else input("Enter MFA One Time Password: ")
        )

    def update_temp_profile(self) -> None:
        """
        Update the temporary profile in the credentials file in case it does
        not exist or is expired
        """
        # _aws_config_parser.temp_profile will be None if the profile does not
        # exist or is expired
        if self._aws_config_parser.temp_profile is None:
            base_sts_client = boto3.client(
                service_name="sts",
                region_name=self._aws_config_parser.aws_region,
                aws_access_key_id=self._aws_config_parser.profile_access_key_id,
                aws_secret_access_key=self._aws_config_parser.profile_secret_access_key,
            )
            session_token_config = {"DurationSeconds": self._config.session_duration}
            if self._use_mfa:
                session_token_config.update(
                    {
                        "SerialNumber": self._aws_config_parser.profile_mfa_serial,
                        "TokenCode": self._otp,
                    }
                )

            result = base_sts_client.get_session_token(**session_token_config)
            self._aws_config_parser.store_temp_profile(**result["Credentials"])

    def _get_role_session(self, account_name: str) -> boto3.Session:
        """Assume a role in the given account and use it to open a session

        Args:
            account_name (str): The account in which the session should be opened
                                This account must be specified in the
                                aws_role_session.toml configuration file.
        """
        account_id = self._config.account_id_for_name(account_name)
        role_to_assume = f"arn:aws:iam::{account_id}:role/{self._role_name}"
        role_credentials = self._sts_client.assume_role(
            RoleArn=role_to_assume,
            RoleSessionName=f"assume-{account_name}",
            DurationSeconds=3600,
        )
        return boto3.Session(
            aws_access_key_id=role_credentials["Credentials"]["AccessKeyId"],
            aws_secret_access_key=role_credentials["Credentials"]["SecretAccessKey"],
            aws_session_token=role_credentials["Credentials"]["SessionToken"],
            region_name=self._aws_config_parser.aws_region,
        )
