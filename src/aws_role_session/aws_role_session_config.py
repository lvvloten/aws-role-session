import os

from tomlkit.toml_file import TOMLFile


class AwsRoleSessionConfig:
    def __init__(self):
        self._config_object = None

    @property
    def _config_path(self):
        return os.path.join(os.path.expanduser("~"), ".aws", "role_session.toml")

    def _get_config(self):
        if not os.path.exists(self._config_path):
            raise RuntimeError(f"Configuration file {self._config_path} does not exist")
        self._config_object = TOMLFile(self._config_path).read()
        # Check for expected sections in the config file
        for section in "defaults", "accounts":
            if section not in self._config_object:
                raise RuntimeError(
                    f"Expected section {section} is not present "
                    f"in configuration file {self._config_path}"
                )

    @property
    def _config(self):
        if self._config_object is None:
            self._get_config()
        return self._config_object

    @property
    def default_region(self):
        return self._get_setting("defaults", "aws_region")

    @property
    def default_profile(self):
        return self._get_setting("defaults", "profile_name")

    @property
    def default_role(self):
        return self._get_setting("defaults", "role_name")

    @property
    def accounts(self):
        return {
            account["name"]: account["id"] for account in self._config.get("accounts")
        }

    @property
    def max_retry_attempts(self):
        # The AWS default for Standard retry mode is 3
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/retries.html
        return int(self._get_setting("optional_settings", "max_retry_attempts", 3))

    def _get_setting(self, section_name, setting_name, default_value=None):
        return (
            self._config[section_name].get(setting_name, default_value)
            if section_name in self._config
            else default_value
        )

    def account_domain(self, account_name):
        return next(
            (
                account["domain"]
                for account in self._config.get("accounts")
                if account["name"] == account_name and "domain" in account
            ),
            None,
        )

    def account_name_for_id(self, account_id):
        return next(
            (
                account["name"]
                for account in self._config.get("accounts")
                if account["id"] == account_id
            ),
            None,
        )
