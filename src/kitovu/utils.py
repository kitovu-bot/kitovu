"""Various utility classes/functions."""

import typing
import getpass
import logging

import keyring
import jsonschema


logger: logging.Logger = logging.getLogger(__name__)


def get_password(plugin: str, identifier: str) -> str:
    """Get the password for the given URL via keyring.

    Args:
       plugin: The name of the plugin requesting a password.
       identifier: An unique identifier (such as an URL) for the connection.
    """
    service = f'kitovu-{plugin}'
    logger.debug(f'Getting password for {service}, identifier {identifier}')
    password: typing.Optional[str] = keyring.get_password(service, identifier)
    if password is None:
        # FIXME handle this in a nicer way
        password = getpass.getpass()
        keyring.set_password(service, identifier, password)
    return password


JsonSchemaType = typing.Dict[str, typing.Any]


class SchemaValidator:
    """A validator for creating and merging errors in schema definitions."""

    def __init__(self, abort: bool = True) -> None:
        self.errors: typing.List[jsonschema.exceptions.ValidationError] = []
        self._abort: bool = abort

    def validate(self, data: typing.Any, schema: JsonSchemaType) -> None:
        """Validates the given data with the schema."""
        validator_type = jsonschema.validators.validator_for(schema)
        self.errors.extend(validator_type(schema).iter_errors(data))
        if self._abort and not self.is_valid:
            self.raise_error()

    def raise_error(self) -> None:
        """Raises itself as an InvalidSettingsError."""
        raise InvalidSettingsError(self)

    @property
    def is_valid(self) -> bool:
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
        super().__init__(validator.error_message)
        self.errors: typing.List[str] = validator.errors


class PluginOperationError(Error):
    pass
