"""Various utility classes/functions."""

import typing
import getpass

import keyring
import jsonschema


def get_password(plugin: str, identifier: str) -> str:
    """Get the password for the given URL via keyring.

    Args:
       plugin: The name of the plugin requesting a password.
       identifier: An unique identifier (such as an URL) for the connection.
    """
    service = f'kitovu-{plugin}'
    password: typing.Optional[str] = keyring.get_password(service, identifier)
    if password is None:
        # FIXME handle this in a nicer way
        password = getpass.getpass()
        keyring.set_password(service, identifier, password)
    return password


class SchemaValidator:
    """A validator for creating and merging errors in schema definitions."""

    def __init__(self, abort: bool) -> None:
        self.errors: typing.List[str] = []
        self.abort: bool = abort

    def validate(self, data: typing.Any, schema: typing.Dict[str, typing.Any]) -> None:
        """Validates the given data with the schema."""
        for error in jsonschema.Draft4Validator(schema).iter_errors(data):
            self.errors.append(error)
        if self.abort and not self.valid:
            raise InvalidSettingsError(self)

    @property
    def valid(self) -> bool:
        """Wether or not the already validated data is valid or not."""
        return not self.errors

    @property
    def error_message(self) -> str:
        """A string representation of all errors."""
        return '\n\n'.join(str(e).replace('\n', '\n\t') for e in self.errors)


class Error(Exception):
    """Base class for kitovu errors."""
    pass


class UsageError(Error):
    """Errors caused by the user."""
    pass


class NoPluginError(UsageError):
    """Thrown when there was no matching plugin found."""
    pass


class InvalidSettingsError(UsageError):
    """Thrown when the settings file is invalid."""

    def __init__(self, validator: SchemaValidator) -> None:
        self.validator: SchemaValidator = validator
        super().__init__(validator.error_message)
