"""Dummy plugin so that we can test the plugin architecture and the rest of kitovu separately."""

import pathlib
import typing

import attr

from kitovu.sync import syncplugin
from kitovu import utils


@attr.s
class Digests:

    local_digest: str = attr.ib()
    remote_digest: str = attr.ib()


class DummyPlugin(syncplugin.AbstractSyncPlugin):

    NAME: str = "dummyplugin"

    def __init__(self,
                 temppath: pathlib.Path,
                 local_digests: typing.Dict[pathlib.Path, str] = None,
                 remote_digests: typing.Dict[pathlib.PurePath, str] = None,
                 connection_schema=None):
        self._temppath = temppath
        self.local_digests = local_digests if local_digests else {
            temppath / "local_dir/test/example1.txt": "1",
            temppath / "local_dir/test/example2.txt": "2",
            temppath / "local_dir/test/example3.txt": "3",
            temppath / "local_dir/test/example4.txt": "4",
        }
        self.remote_digests = remote_digests if remote_digests else {
            pathlib.PurePath("remote_dir/test/example1.txt"): "1",
            pathlib.PurePath("remote_dir/test/example2.txt"): "2",
            pathlib.PurePath("remote_dir/test/example3.txt"): "3",
            pathlib.PurePath("remote_dir/test/example4.txt"): "4",
        }
        self.is_connected: bool = False
        self._connection_schema = connection_schema if connection_schema else {}

        self.mtime = None
        self.error_connect = False
        self.error_list_path = False
        self.error_create_remote_digest = False

    def configure(self, info: typing.Dict[str, typing.Any]) -> None:
        pass

    def connect(self) -> None:
        if self.error_connect:
            raise utils.PluginOperationError("Could not connect")

        assert not self.is_connected
        self.is_connected = True

    def disconnect(self) -> None:
        assert self.is_connected
        self.is_connected = False

    def create_local_digest(self, path: pathlib.Path) -> str:
        assert self.is_connected
        return self.local_digests.get(path, '')

    def create_remote_digest(self, path: pathlib.PurePath) -> str:
        if self.error_create_remote_digest:
            raise utils.PluginOperationError("Could not create remote digest")

        assert self.is_connected
        return self.remote_digests[path]

    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        if self.error_list_path:
            raise utils.PluginOperationError("Could not list path")

        assert self.is_connected
        for filename in sorted(self.remote_digests):
            if str(filename).startswith(str(path)):
                yield filename

    def retrieve_file(self,
                      path: pathlib.PurePath,
                      fileobj: typing.IO[bytes]) -> typing.Optional[int]:
        assert self.is_connected
        remote_digest = self.remote_digests[path]
        fileobj.write(f"{path}\n{remote_digest}".encode("utf-8"))
        self.local_digests[pathlib.Path(fileobj.name)] = remote_digest
        return self.mtime

    def connection_schema(self) -> utils.JsonType:
        return self._connection_schema
