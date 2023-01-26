import os
from typing import Any, Optional, Union

import toml
from botocore import configprovider
from jsonschema import validate

# Schema to validate the configuration file
JSON_SCHEMA = {
    "definitions": {},
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Configuration file format for AwsRoleSession class",
    "type": "object",
    "required": ["defaults", "settings"],
    "additionalProperties": False,
    "properties": {
        "defaults": {
            "type": "object",
            "required": ["profile_name", "role_name"],
            "additionalProperties": False,
            "properties": {
                "profile_name": {"type": "string"},
                "role_name": {"type": "string"},
                "use_mfa": {"type": "boolean"},
            },
        },
        "settings": {
            "type": "object",
            "required": ["accounts"],
            "additionalProperties": False,
            "properties": {
                "accounts": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/account"},
                    "minItems": 1,
                    "uniqueItems": True,
                },
                "max_retry_attempts": {"type": "integer"},
                "session_duration": {
                    "type": "integer",
                    "minimum": 900,
                    "maximum": 129600,
                },
            },
        },
    },
    "$defs": {
        "account": {
            "type": "object",
            "required": ["name", "id"],
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "id": {"pattern": "^[0-9]{12}$"},
                "role": {"type": "string"},
                "category": {"type": "string"},
            },
        }
    },
}
# The name of the configuration file.
CONFIG_FILE_NAME = "aws_role_session.toml"


class AwsRoleSessionConfig:
    SettingValue = Union[str, int, bool, None]

    def __init__(self, configuration: Optional[dict] = None) -> None:
        self._configuration = None
        self.configuration = configuration

    @property
    def configuration(self) -> dict[str, Any]:
        """
        The aws_role_session configuration in JSON format.
        The configuration is typically retrieved from the configuration file,
        but can also be passed as a parameter when the class is initialized.
        """
        if self._configuration is None:
            self.configuration = toml.load(self._config_path)
        return self._configuration

    @configuration.setter
    def configuration(self, value: dict) -> None:
        if value is not None:
            # The jsonschema validate function will raise an exception in case
            # the configuration is not valid
            validate(value, JSON_SCHEMA)
        self._configuration = value

    @property
    def _config_path(self) -> str:
        # The configuration file is expected to be im the default AWS CLI configuration directory
        result = os.path.join(os.path.expanduser("~"), ".aws", CONFIG_FILE_NAME)
        if not os.path.exists(result):
            raise FileNotFoundError(
                f"Configuration file {result} does not exist. The configuration "
                "is required and can be specified in this file, or passed as a dict"
                "variable when initializing the class."
            )
        return result

    def _get_setting(
        self,
        section_name: str,
        setting_name: str,
        default_value: SettingValue = None,
    ) -> SettingValue:
        return (
            self.configuration[section_name].get(setting_name, default_value)
            if section_name in self.configuration
            else default_value
        )

    @property
    def default_use_mfa(self) -> bool:
        """
        The default configuration file setting for using MFA
        """
        return self._get_setting("defaults", "use_mfa", True)

    @property
    def default_profile(self) -> str:
        """
        The default configuration file setting for AWS credentials profile
        """
        return self._get_setting("defaults", "profile_name")

    @property
    def default_role(self) -> str:
        """
        The default configuration file setting for the remote role that is to be assumed
        """
        return self._get_setting("defaults", "role_name")

    @property
    def accounts(self) -> list[dict]:
        """
        List of the accounts that are configured in the configuration file
        """
        return self._get_setting("settings", "accounts")

    def account_role(self, account_name: str) -> Union[str, None]:
        """Obtain the role name to be assumed in an account.

        Args:
            account_name (str): The account for which the role is obtained

        Returns:
            Returns the role that is configured for the given account
            Or else the default role if it is configured
            Or else None if neither is configured
        """
        role = next(
            (
                account["role"]
                for account in self.accounts
                if account["name"] == account_name and "role" in account
            ),
            None,
        )
        return self.default_role if role is None else role

    @property
    def max_retry_attempts(self) -> int:
        """Number of retries that are attempted in boto3 calls in case of intermittent failures

        This can optionally be configured in the configuration file. The default value is 3.
        """
        # The AWS default for Standard retry mode is 3
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/retries.html
        return int(self._get_setting("settings", "max_retry_attempts", 3))

    @property
    def session_duration(self) -> int:
        # The AWS default for Session Duration is 43200
        # https://docs.aws.amazon.com/STS/latest/APIReference/API_GetSessionToken.html
        return int(self._get_setting("settings", "session_duration", 43200))

    def account_category(self, account: str) -> str:
        """Find an account category by either account name or account id"""
        return next(
            (
                acc["category"]
                for acc in self.accounts
                if account in (acc["name"], acc["id"]) and "category" in acc
            ),
            None,
        )

    def account_name_for_id(self, account_id: str) -> str:
        return next(
            (
                account["name"]
                for account in self.accounts
                if account["id"] == account_id
            ),
            None,
        )

    def account_id_for_name(self, account_name: str) -> str:
        return next(
            (
                account["id"]
                for account in self.accounts
                if account["name"] == account_name
            ),
            None,
        )
