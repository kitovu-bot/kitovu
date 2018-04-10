"""Dummy plugin so that we can test the plugin architecture and the rest of kitovu separately."""

import pathlib
import typing

import attr

from kitovu.sync import syncplugin


@attr.s
class Digests:

    local_digest: str = attr.ib()
    remote_digest: str = attr.ib()


class DummyPlugin(syncplugin.AbstractSyncPlugin):

    def __init__(self):
        super().__init__()
        self.paths: typing.Dict[pathlib.PurePath, Digests] = {
            pathlib.PurePath("example1.txt"): Digests("1", "1"),
            pathlib.PurePath("example2.txt"): Digests("2", "2"),
            pathlib.PurePath("example3.txt"): Digests("3", "3"),
            pathlib.PurePath("example4.txt"): Digests("4", "4"),
        }
        self.is_connected: bool = False

    def configure(self, info: typing.Dict[str, typing.Any]) -> None:
        pass

    def connect(self) -> None:
        assert not self.is_connected
        self.is_connected = True

    def disconnect(self) -> None:
        assert self.is_connected
        self.is_connected = False

    def create_local_digest(self, path: pathlib.Path) -> str:
        assert self.is_connected
        return self.paths[path].local_digest

    def create_remote_digest(self, path: pathlib.PurePath) -> str:
        assert self.is_connected
        return self.paths[path].remote_digest

    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        assert self.is_connected
        yield from sorted(self.paths)

    def retrieve_file(self, path: pathlib.PurePath, fileobj: typing.IO[bytes]) -> None:
        assert self.is_connected
        remote_digest = self.paths[path].remote_digest
        fileobj.write(f"{path}\n{remote_digest}".encode("utf-8"))
