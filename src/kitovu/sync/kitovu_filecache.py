"""FileCache keeps track of the state of the files, remotely and locally. It exists to determine if the local file
has been changed between two synchronisation processes and allows for a conflict handling accordingly."""

import appdirs
from enum import Enum
import json
import pathlib
import typing

from kitovu.sync import syncplugin
from kitovu import utils

# sync-process:
# every time we sync something, the FileCache gets read, upon which kitovu decides what needs to be downloaded.
# The files get downloaded, for each file, the FileCache gets updated for the files that were synchronised.


class Filestate(Enum):
    """Used to discern in which places files have changed"""
    LOCAL = 1
    REMOTE = 2
    BOTH = 3
    NONE = 4


# refactor with attrs.?
class File:

    def __init__(self, local_digest_at_synctime: str,
                 relative_path_with_filename: pathlib.PurePath,
                 plugin: syncplugin.AbstractSyncPlugin) -> None:
        self._cached_digest = local_digest_at_synctime # value
        self._relative_path_with_filename: pathlib.PurePath = relative_path_with_filename  # key
        self._plugin = plugin  # value
        self._remote_digest = ""
        self._local_digest = ""

    def to_dict(self) -> typing.Dict[str, str]:
        return {"plugin": self._plugin.name,
                "digest": self._cached_digest}


class FileCache:

    def __init__(self, filename: pathlib.Path):
        self._filename: pathlib.Path = filename
        self._data: typing.Dict[pathlib.PurePath, File] = {}

    def write(self) -> None:
        """"Writes the data-dict to JSON."""
        json_data: typing.Dict[str, typing.Dict[str, str]] = {}

        for key, value in self._data.items():
            json_data[str(key)] = value.to_dict()

        with self._filename.open("w") as f:
            json.dump(json_data, f)

    def load(self) -> None:
        """What is called first when the synchronisation process is started."""
        with self._filename.open("r") as f:
            json_data = json.load(f)
        for key, value in json_data.items():
            digest: str = value["digest"]
            plugin: str = value["plugin"]
            self._data[pathlib.PurePath(key)] = File(local_digest_at_synctime=digest, plugin=plugin) # should be of type AbstractSyncPlugin

    def modify(self):
        pass

    def discover_changes(self, path: pathlib.PurePath) -> Filestate:
        # use path as index into already loaded _data
        # get cached_digest, compare it to file that is synchronised
        # return ENUM: LOCAL; REMOTE; BOTH; NONE
        pass





