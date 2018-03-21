"""Loading and handling of sychronization plugins."""

import abc
import pathlib
import typing


class AbstractSyncPlugin(metaclass=abc.ABCMeta):

    """The specification/"interface" a synchronization plugin implements.

    Every abstract method in this class is a plugin hook.
    """

    @abc.abstractmethod
    def connect(self, url: str, options: dict) -> None:
        """Connect to the given URL.

        This should raise an appropriate exception if the connection failed.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Close any open connection."""
        raise NotImplementedError

    @abc.abstractmethod
    def create_local_digest(self, path: pathlib.Path) -> str:
        """Create a digest for the given local file."""
        raise NotImplementedError

    @abc.abstractmethod
    def create_remote_digest(self, path: pathlib.PurePath) -> str:
        """Create a digest for the given remote file."""
        raise NotImplementedError

    @abc.abstractmethod
    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        """Get a list of files in the given remote path."""
        raise NotImplementedError

    @abc.abstractmethod
    def retrieve_file(self, path: pathlib.PurePath, fileobj: typing.IO[bytes]) -> None:
        """Retrieve the given remote file."""
        raise NotImplementedError
