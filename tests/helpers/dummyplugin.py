"""Dummy plugin so that we can separately test kitovu and the plugin architecture."""

import attr
import pathlib
import typing
from kitovu.sync import syncplugin


class DummyPlugin(syncplugin.AbstractSyncPlugin):
    def configure(self, info: typing.Dict[str, typing.Any]) -> None:
        pass

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def create_local_digest(self, path: pathlib.Path) -> str:
        pass

    def create_remote_digest(self, path: pathlib.PurePath) -> str:
        pass

    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        pass

    def retrieve_file(self, path: pathlib.PurePath, fileobj: typing.IO[bytes]) -> None:
        pass

