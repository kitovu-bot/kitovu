"""FileCache keeps track of the state of the files, remotely and locally.

It exists to determine if the local file has been changed between two synchronisation processes
and allows for a conflict handling accordingly.

8 cases are possible:

Special Cases:
---------------
1. remote deleted (triggers exception), local exists: REMOTE_CHANGED

2. remote deleted (triggers exception), local exists AND changed (local_digest and cached_digest differ): BOTH_CHANGED
case 1 and 2 special, and are dealt with separately in syncing.py.

Cases 1 and 2 are not handled at the moment - see https://jira.keltec.ch/jira/browse/EPJ-77

Normal Cases:
--------------
3. new file remote, local none: NEW, download file. This is the default case.

4. remote B, local A - remote digest and local digest differ,
but local digest and cached digest are same: REMOTE_CHANGED, download.

5. remote and local same: NO_CHANGES

Files changed in-between:
-------------------------
6. remote A unchanged, local changed A' - remote digest and cached digest are the same,
but local digest and cached digest differ: LOCAL_CHANGED

7. remote B, local changed A' - remote digest and cached digest differ,
local digest and cached digest differ: BOTH_CHANGED
"""

import attr
from enum import Enum
import json
import pathlib
import typing

from kitovu.sync import syncplugin


class FileState(Enum):
    """Used to discern in which places files have changed."""

    NEW = 3
    REMOTE_CHANGED = 4
    NO_CHANGES = 5
    LOCAL_CHANGED = 6
    BOTH_CHANGED = 7


# #FIXME refactor with attrs.?
@attr.s
class File:

    def __init__(self, local_digest_at_synctime: str,
                 relative_path_with_filename: pathlib.Path,
                 plugin_name: str) -> None:
        self._cached_digest = attr.ib()
        self._relative_path_with_filename: pathlib.Path = attr.ib()
        self.plugin_name = attr.ib()
        self._remote_digest = ""
        self._local_digest = ""

    def to_dict(self) -> typing.Dict[str, str]:
        return {"plugin": self.plugin_name,
                "digest": self._cached_digest}


class FileCache:

    def __init__(self, filename: pathlib.Path):
        self._filename: pathlib.Path = filename
        self._data: typing.Dict[pathlib.Path, File] = {}

    def _compare_digests(self, remote_digest: str, local_digest: str, cached_digest: str) -> FileState:
        local_changed: bool = local_digest != cached_digest
        remote_changed: bool = remote_digest != cached_digest
        if not remote_changed and not local_changed:  # case 5 above
            return FileState.NO_CHANGES
        elif remote_changed and not local_changed:  # case 4 above
            return FileState.REMOTE_CHANGED
        elif not remote_changed and local_changed:  # case 6 above
            return FileState.LOCAL_CHANGED
        elif remote_changed and local_changed:  # case 7 above
            return FileState.BOTH_CHANGED

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
            plugin_name: str = value["plugin"]
            self._data[pathlib.Path(key)] = File(local_digest_at_synctime=digest, plugin_name=plugin_name)

    def modify(self, path: pathlib.Path, plugin: syncplugin.AbstractSyncPlugin, local_digest_at_synctime: str):
        file = File(local_digest_at_synctime=local_digest_at_synctime, plugin_name=plugin.NAME)
        self._data[path] = file

    def discover_changes(self,
                         local_full_path: pathlib.Path,
                         remote_full_path: pathlib.PurePath,
                         plugin: syncplugin.AbstractSyncPlugin) -> FileState:
        """Check if the file that is currently downloaded (path-argument) has changed.

        Change is discovered between local file cache and local file."""
        if not local_full_path.exists():
            return FileState.NEW

        file: File = self._data[local_full_path]
        cached_digest: str = file["digest"]
        if plugin.NAME != file.plugin_name:
            raise AssertionError(f"The cached plugin name '{file.plugin_name}' of the file {local_full_path} "
                                 f"doesn't match the plugin name '{plugin.NAME}'.")

        remote_digest: str = plugin.create_remote_digest(remote_full_path)
        local_digest: str = plugin.create_local_digest(local_full_path)
        return self._compare_digests(remote_digest, local_digest, cached_digest)

