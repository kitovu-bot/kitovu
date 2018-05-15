"""Various utility classes/functions."""

import typing
import getpass
import logging
import pathlib

import keyring
import jsonschema


logger: logging.Logger = logging.getLogger(__name__)


def get_password(plugin: str, identifier: str, prompt: str) -> str:
    """Get the password for the given URL via keyring.

    Args:
       plugin: The name of the plugin requesting a password.
       identifier: An unique identifier (such as an URL) for the connection.
       prompt: An additional prompt to display to the user.
    """
    service = f'kitovu-{plugin}'
    logger.debug(f'Getting password for {service}, identifier {identifier}')
    password: typing.Optional[str] = keyring.get_password(service, identifier)
    if password is None:
        password = getpass.getpass(f"Enter password for {plugin} ({prompt}): ")
        keyring.set_password(service, identifier, password)
    return password


def sanitize_filename(name: pathlib.PurePath) -> pathlib.PurePath:
    r"""Replace invalid filename characters.

    Note: This does not escape directory separators (/ and \).
    """
    name_str: str = str(name)
    # Bad characters taken from Windows, there are even fewer on Linux
    # See also
    # https://en.wikipedia.org/wiki/Filename#Reserved_characters_and_words
    bad_chars = ':*?"<>|'
    for bad_char in bad_chars:
        name_str = name_str.replace(bad_char, '_')
    return pathlib.PurePath(name_str)


JsonType = typing.Dict[str, typing.Any]


class SchemaValidator:
    """A validator for creating and merging errors in schema definitions."""

    def __init__(self, abort: bool = True) -> None:
        self.errors: typing.List[jsonschema.exceptions.ValidationError] = []
        self._abort: bool = abort

    def validate(self, data: typing.Any, schema: JsonType) -> None:
        validator_type = jsonschema.validators.validator_for(schema)
        self.errors.extend(validator_type(schema).iter_errors(data))
        if self._abort and not self.is_valid:
            self.raise_error()

    def raise_error(self) -> None:
        raise InvalidSettingsError(self)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def error_message(self) -> str:
        return '\n\n'.join(str(e).replace('\n', '\n\t') for e in self.errors)


class Error(Exception):
    """Base class for kitovu errors."""


class UsageError(Error):
    """Errors caused by the user."""


class NoPluginError(UsageError):
    """Thrown when there was no matching plugin found."""


class InvalidSettingsError(UsageError):
    """Thrown when the settings file is invalid."""

    def __init__(self, validator: SchemaValidator) -> None:
        super().__init__(validator.error_message)
        self.errors: typing.List[str] = validator.errors


class PluginOperationError(Error):
    """Thrown when something in a plugin fails."""


class AuthenticationError(PluginOperationError):
    """Thrown when the authentication could not be completed."""
