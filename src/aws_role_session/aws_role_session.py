# pylint: disable=missing-function-docstring
import boto3
import pyotp
from botocore.config import Config

from .aws_config_parser import AwsConfigParser
from .aws_role_session_config import AwsRoleSessionConfig


class AwsRoleSession:
    def __init__(
        self,
        profile_name=None,
        role_name=None,
    ):
        self._config = AwsRoleSessionConfig()
        self._role_name = (
            role_name if role_name is not None else self._config.default_role
        )
        profile = (
            profile_name if profile_name is not None else self._config.default_profile
        )
        self._aws_config_parser = AwsConfigParser(profile)
        self._sts_client_object = None
        self._role_session_object = None
        self._role_session_account = None

    @property
    def _retry_config(self):
        return Config(
            retries={
                "max_attempts": self._config.max_retry_attempts,
                "mode": "standard",
            }
        )

    def get_client(self, account_name, service_name):
        return self._role_session(account_name).client(
            service_name=service_name,
            config=self._retry_config,
        )

    def get_resource(self, account_name, service_name):
        return self._role_session(account_name).resource(
            service_name=service_name,
            config=self._retry_config,
        )

    @property
    def _sts_client(self):
        if (
            self._sts_client_object is None
            or not self._aws_config_parser.temp_profile_is_valid
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

    def _role_session(self, account_name):
        if (
            self._role_session_object is None
            or self._role_session_account != account_name
        ):
            self._role_session_object = self._get_role_session(account_name)
            self._role_session_account = account_name
        return self._role_session_object

    def update_temp_profile(self):
        if not self._aws_config_parser.temp_profile_is_valid:
            otp = pyotp.TOTP(self._aws_config_parser.profile_mfa_key).now()
            base_sts_client = boto3.client(
                service_name="sts",
                region_name=self._aws_config_parser.aws_region,
                aws_access_key_id=self._aws_config_parser.profile_access_key_id,
                aws_secret_access_key=self._aws_config_parser.profile_secret_access_key,
            )
            result = base_sts_client.get_session_token(
                DurationSeconds=43200,
                SerialNumber=self._aws_config_parser.profile_mfa_serial,
                TokenCode=otp,
            )
            self._aws_config_parser.store_temp_profile(**result["Credentials"])

    def _obtain_temp_credentials(self):
        otp = pyotp.TOTP(self._aws_config_parser.profile_mfa_key).now()
        base_sts_client = boto3.client(
            service_name="sts",
            region_name=self._aws_config_parser.aws_region,
            aws_access_key_id=self._aws_config_parser.profile_access_key_id,
            aws_secret_access_key=self._aws_config_parser.profile_secret_access_key,
        )
        result = base_sts_client.get_session_token(
            DurationSeconds=43200,
            SerialNumber=self._aws_config_parser.profile_mfa_serial,
            TokenCode=otp,
        )
        return result["Credentials"]

    def _get_role_session(self, account_name):
        role_to_assume = (
            f"arn:aws:iam::{self._config.accounts[account_name]}:role/{self._role_name}"
        )
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
