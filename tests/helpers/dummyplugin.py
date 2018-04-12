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

    def __init__(self,
                 local_digests: typing.Dict[pathlib.PurePath, str]=None,
                 remote_digests: typing.Dict[pathlib.PurePath, str]=None):
        super().__init__()
        self.local_digests = local_digests if local_digests else {
            pathlib.PurePath("local_dir/test/example1.txt"): "1",
            pathlib.PurePath("local_dir/test/example2.txt"): "2",
            pathlib.PurePath("local_dir/test/example3.txt"): "3",
            pathlib.PurePath("local_dir/test/example4.txt"): "4",
        }
        self.remote_digests = remote_digests if remote_digests else {
            pathlib.PurePath("remote_dir/test/example1.txt"): "1",
            pathlib.PurePath("remote_dir/test/example2.txt"): "2",
            pathlib.PurePath("remote_dir/test/example3.txt"): "3",
            pathlib.PurePath("remote_dir/test/example4.txt"): "4",
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
        return self.local_digests.get(path, '')

    def create_remote_digest(self, path: pathlib.PurePath) -> str:
        assert self.is_connected
        return self.remote_digests[path]

    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        assert self.is_connected
        for filename in sorted(self.remote_digests):
            if str(filename).startswith(str(path)):
                yield filename

    def retrieve_file(self, path: pathlib.PurePath, fileobj: typing.IO[bytes]) -> None:
        assert self.is_connected
        remote_digest = self.remote_digests[path]
        fileobj.write(f"{path}\n{remote_digest}".encode("utf-8"))

    def connection_schema(self) -> typing.Dict[str, typing.Any]:
        return {}
