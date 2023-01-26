import logging
from logging import NullHandler

from .aws_role_session import AwsRoleSession
from .aws_role_session_config import AwsRoleSessionConfig

__author__ = "Lucas van Braam van Vloten (lucas2@dds.nl)"
__license__ = "MIT"
__version__ = "0.0.8"

__all__ = (
    "AwsRoleSession",
)

logging.getLogger(__name__).addHandler(NullHandler())
