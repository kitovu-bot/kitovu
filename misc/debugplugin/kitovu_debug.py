import pathlib
import typing

from kitovu.sync import syncplugin


class DebugPlugin(syncplugin.AbstractSyncPlugin):

    def connect(self, url: str, options: dict) -> None:
        print(f"Connecting to {url} with {options}")

    def disconnect(self) -> None:
        print("Disconnecting")

    def create_local_digest(self, path: pathlib.Path) -> str:
        print(f"Creating local digest for {path}")
        return 'exampledigest'

    def create_remote_digest(self, path: pathlib.PurePath) -> str:
        """Create a digest for the given remote file."""
        print(f"Creating remote digest for {path}")
        return 'exampledigest'

    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        print(f"Listing {path}")
        return [pathlib.PurePath('/examplefile')]

    def retrieve_file(self, path: pathlib.PurePath, fileobj: typing.IO[bytes]) -> None:
        print(f"Retrieving {path} to {fileobj}")
        fileobj.write(b'examplecontents')
