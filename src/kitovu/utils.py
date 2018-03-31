"""Various utility classes/functions."""

import typing


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

    pass


class MissingSettingKeysError(InvalidSettingsError):

    """Thrown when the settings have missing required keys."""

    def __init__(self, missing_keys: typing.List[str]) -> None:
        self.missing_keys = missing_keys

        keys = ', '.join(self.missing_keys)
        super().__init__(f'Missing keys: {keys}')


class UnknownSettingKeysError(InvalidSettingsError):

    """Thrown when the settings have unknown keys."""

    def __init__(self, unknown_keys: typing.List[str]) -> None:
        self.unknown_keys = unknown_keys

        keys = ', '.join(self.unknown_keys)
        super().__init__(f'Unknown keys: {keys}')
