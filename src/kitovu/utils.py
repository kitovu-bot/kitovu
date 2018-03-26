"""Various utility classes/functions."""


class Error(Exception):

    """Base class for kitovu errors."""

    pass


class UsageError(Error):

    """Errors caused by the user."""

    pass


class NoPluginError(UsageError):

    """Thrown when there was no matching plugin found."""

    pass
