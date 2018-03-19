"""Loading and handling of sychronization plugins."""

import pathlib
import typing

import pluggy


hookspec = pluggy.HookspecMarker("kitovu")
manager: pluggy.PluginManager = None


class SyncPluginSpec:

    """The specification/"interface" a synchronization plugin implements.

    Every method in this class is a plugin hook.
    """

    @hookspec
    def connect(self, url: str, options: dict) -> None:
        """Connect to the given URL.

        This should raise an appropriate exception if the connection failed.
        """
        raise NotImplementedError

    @hookspec
    def disconnect(self) -> None:
        """Close any open connection."""
        raise NotImplementedError

    @hookspec
    def create_local_digest(self, path: pathlib.Path) -> str:
        """Create a digest for the given local file."""
        raise NotImplementedError

    @hookspec
    def create_remote_digest(self, path: pathlib.Path) -> str:
        """Create a digest for the given remote file."""
        raise NotImplementedError

    @hookspec
    def list_path(self, path: pathlib.Path) -> typing.Iterable[pathlib.Path]:
        """Get a list of files in the given remote path."""
        raise NotImplementedError

    @hookspec
    def retrieve_file(self, path: pathlib.Path, fileobj: typing.IO[str]) -> None:
        """Retrieve the given remote file."""
        raise NotImplementedError


def init() -> None:
    """Load plugins and initialize the global PluginManager instance."""
    global manager
    manager = pluggy.PluginManager("kitovu")
    manager.add_hookspecs(SyncPluginSpec)
