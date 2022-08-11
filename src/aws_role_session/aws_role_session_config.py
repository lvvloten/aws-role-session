import os
from typing import Optional, Union, Any

import toml
from jsonschema import validate

# Schema to validate the aws_role_session.toml configuration file
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
                "category": {"type": "string"},
            },
        }
    },
}


class AwsRoleSessionConfig:
    SettingValue = Union[str, int, bool, None]

    def __init__(self, configuration: Optional[dict] = None) -> None:
        self._configuration = None
        self.configuration = configuration

    @property
    def _config_path(self) -> str:
        result = os.path.join(os.path.expanduser("~"), ".aws", "aws_role_session.toml")
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
    def configuration(self) -> dict[str, Any]:
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
    def default_use_mfa(self) -> bool:
        return self._get_setting("defaults", "use_mfa", True)

    @property
    def default_profile(self) -> str:
        return self._get_setting("defaults", "profile_name")

    @property
    def default_role(self) -> str:
        return self._get_setting("defaults", "role_name")

    @property
    def accounts(self) -> list[dict]:
        return self._get_setting("settings", "accounts")

    @property
    def max_retry_attempts(self) -> int:
        # The AWS default for Standard retry mode is 3
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/retries.html
        return int(self._get_setting("settings", "max_retry_attempts", 3))

    @property
    def session_duration(self) -> int:
        # The AWS default for Session Duration is 43200
        # https://docs.aws.amazon.com/STS/latest/APIReference/API_GetSessionToken.html
        return int(self._get_setting("settings", "session_duration", 43200))

    def account_category(self, account_name: str) -> str:
        return next(
            (
                account["ccategory"]
                for account in self.accounts
                if account["name"] == account_name and "category" in account
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
