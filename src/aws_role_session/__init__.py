import logging
from logging import NullHandler

from .aws_role_session import AwsRoleSession

__author__ = "Lucas van Braam van Vloten (lucas2@dds.nl)"
__license__ = "MIT"
__version__ = "0.0.2"

__all__ = (
    "AwsRoleSession",
)

logging.getLogger(__name__).addHandler(NullHandler())
