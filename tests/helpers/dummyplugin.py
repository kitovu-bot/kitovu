"""Dummy plugin so that we can test the plugin architecture and the rest of kitovu separately."""

import attr
from kitovu.sync import syncplugin
import pathlib
import typing


@attr.s
class Digests:

    """test-class that provides the local and remote digests as strings"""

    local_digest: str = attr.ib()
    remote_digest: str = attr.ib()


@attr.s
class DummyPlugin(syncplugin.AbstractSyncPlugin):

    """provides a fake connection with hard-coded filenames for testing."""

    paths: typing.Dict[pathlib.PurePath, Digests] = attr.ib(attr.Factory(lambda: {
        pathlib.PurePath("example1.txt"): Digests("1", "1"),
        pathlib.PurePath("example2.txt"): Digests("2", "2"),
        pathlib.PurePath("example3.txt"): Digests("3", "3"),
        pathlib.PurePath("example4.txt"): Digests("4", "4"),
    }))
    connection_state: bool = attr.ib(False)

    def configure(self, info: typing.Dict[str, typing.Any]) -> None:
        pass

    def connect(self) -> None:
        self.connection_state = True

    def disconnect(self) -> None:
        assert self.connection_state
        self.connection_state = False

    def create_local_digest(self, path: pathlib.PurePath) -> str:
        assert self.connection_state
        return self.paths[path].local_digest

    def create_remote_digest(self, path: pathlib.PurePath) -> str:
        assert self.connection_state
        return self.paths[path].remote_digest

    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        assert self.connection_state
        for n in self.paths:
            yield n

    def retrieve_file(self, path: pathlib.PurePath, fileobj: typing.IO[bytes]) -> None:
        # for the sake of testing, it writes gibberish into the file
        assert self.connection_state
        remote_digest = self.paths[path].remote_digest
        fileobj.write(f"{path}\n{remote_digest}")

