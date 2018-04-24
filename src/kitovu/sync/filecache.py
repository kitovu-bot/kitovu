"""FileCache keeps track of the state of the files, remotely and locally.

It exists to determine if the local file has been changed between two synchronisation processes
and allows for a conflict handling accordingly.

8 cases are possible:

Special Cases:
---------------
1. remote deleted (triggers exception), local exists: REMOTE

2. remote deleted (triggers exception), local exists AND changed (local_digest and cached_digest differ): BOTH
case 1 and 2 special, and are dealt with separately, FIXME externally

Normal Cases:
--------------
3. new file remote, local none: REMOTE, download file. This is the default case.

4. remote B, local A - remote digest and local digest differ,
but local digest and cached digest are same: REMOTE, download.

5. remote and local same: NONE

Files changed in-between:
-------------------------
6. remote A unchanged, local changed A' - remote digest and cached digest are  the same,
but local digest and cached digest differ: LOCAL

7. remote B, local changed A' - remote digest and cached digest differ, local digest and cached digest differ: BOTH

8. remote B, local B => remote digest and cached digest same,
but local digest and cached digest differ: update file cache

Case 8 is basically the same as 6, it simply triggers the user's decision and needs to update the file cache

"""

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


# #FIXME refactor with attrs.?
class File:

    def __init__(self, local_digest_at_synctime: str,
                 relative_path_with_filename: pathlib.Path,
                 plugin: syncplugin.AbstractSyncPlugin) -> None:
        self._cached_digest = local_digest_at_synctime  # dict-value
        self._relative_path_with_filename: pathlib.Path = relative_path_with_filename  # dict-key
        self._plugin = plugin  # dict-value
        self._remote_digest = ""
        self._local_digest = ""

    def to_dict(self) -> typing.Dict[str, str]:
        return {"plugin": self._plugin.name,  # FIXME doesn't resolve
                "digest": self._cached_digest}


class FileCache:

    def __init__(self, filename: pathlib.Path, plugins: typing.Dict[str, syncplugin.AbstractSyncPlugin]):
        self._filename: pathlib.Path = filename
        self._data: typing.Dict[pathlib.Path, File] = {}
        self._plugins = plugins

    def _compare_digests(self, remote_digest: str, local_digest: str, cached_digest: str) -> Filestate:
        local_changed: bool = local_digest != cached_digest
        remote_changed: bool = remote_digest != cached_digest
        if not remote_changed and not local_changed:  # case 5
            return Filestate.NONE
        elif remote_changed and not local_changed:  # case 4
            return Filestate.REMOTE
        elif not remote_changed and local_changed:  # case 6
            return Filestate.LOCAL
        elif remote_changed and local_changed:  # case 7
            return Filestate.BOTH

    def write(self) -> None:
        """"Writes the data-dict to JSON."""
        json_data: typing.Dict[str, typing.Dict[str, str]] = {}

        for key, value in self._data.items():
            json_data[str(key)] = value.to_dict()

        with self._filename.open("w") as f:
            json.dump(json_data, f)

    def load(self) -> None:
        """This is called first when the synchronisation process is started."""
        with self._filename.open("r") as f:
            json_data = json.load(f)
        for key, value in json_data.items():
            digest: str = value["digest"]
            plugin: str = value["plugin"]
            self._data[pathlib.Path(key)] = File(local_digest_at_synctime=digest, plugin=plugin)
            # FIXME should be of type AbstractSyncPlugin - conversion needed?

    def modify(self, path: pathlib.Path, plugin: syncplugin.AbstractSyncPlugin, local_digest_at_synctime: str):
        file = File(local_digest_at_synctime=local_digest_at_synctime, plugin=plugin)
        self._data[path] = file

    def discover_changes(self, path: pathlib.Path, plugin: syncplugin.AbstractSyncPlugin) -> Filestate:
        """Check if the file that is currently downloaded (path-argument) has changed.

        Change is discovered between local filecache and local file."""
        # FIXME error handling to see if _data has been loaded already

        # use path as index into already loaded _data
        file: File = self._data[path]
        cached_digest: str = file["digest"]

        # get cached_digest, compare it to file that is synchronised
        remote_digest: str = plugin.create_remote_digest(path)
        local_digest: str = plugin.create_local_digest(path)
        return self._compare_digests(remote_digest, local_digest, cached_digest)

