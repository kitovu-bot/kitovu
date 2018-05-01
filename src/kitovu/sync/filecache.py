"""FileCache keeps track of the state of the files, remotely and locally.

It exists to determine if the local file has been changed between two synchronisation processes
and allows for a conflict handling accordingly.

There are various cases to consider how files can have changed:

Remote file deleted
-------------------

1. remote file was deleted (triggers exception)
   local file exists (but is unchanged):
-> REMOTE_CHANGED

2. remote file deleted was (triggers exception)
   local file exists AND has changed (local_digest and cached_digest differ):
-> BOTH_CHANGED

Those two cases are not handled at the moment - see https://jira.keltec.ch/jira/browse/EPJ-77

Normal cases
------------

3. new remote file
   does not exist locally:
-> NEW (file gets downloaded)

4. remote file has contents B (remote digest and local digest differ)
   local file has contents A (local digest and cached digest are the same)
-> REMOTE_CHANGED (file gets downloaded)

5. remote file has contents A
   remote file has contents A (same content)
-> NO_CHANGES (do nothing)

Local file changed
------------------

6. remote file has contents A (unchanged, remote and cached digest are the same)
   local file has contents A' (changed, local and cached digest differ)
-> LOCAL_CHANGED (do nothing)

7. remote file has contents B (remote changed, remote and cached digest differ)
   local file has contents  A' (local changed, local and cached digest differ)
-> BOTH_CHANGED (conflict!)
"""

import enum
import json
import pathlib
import typing

import attr

from kitovu.sync import syncplugin


class FileState(enum.Enum):
    """Used to discern in which places files have changed."""

    NEW = 3
    REMOTE_CHANGED = 4
    NO_CHANGES = 5
    LOCAL_CHANGED = 6
    BOTH_CHANGED = 7


@attr.s
class File:

    cached_digest: str = attr.ib()  # local digest at synctime
    plugin_name: str = attr.ib()

    def to_dict(self) -> typing.Dict[str, str]:
        return {"plugin": self.plugin_name,
                "digest": self.cached_digest}


class FileCache:

    def __init__(self, filename: pathlib.Path) -> None:
        self._filename: pathlib.Path = filename
        self._data: typing.Dict[pathlib.Path, File] = {}

    def _compare_digests(self,
                         remote_digest: str,
                         local_digest: str,
                         cached_digest: str) -> FileState:
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
        else:
            raise AssertionError(f"Failed to compare digests! remote: {remote_digest}, "
                                 f"local: {local_digest}, cached {cached_digest}")

    def write(self) -> None:
        """"Writes the data-dict to JSON."""
        json_data: typing.Dict[str, typing.Dict[str, str]] = {}

        for key, value in self._data.items():
            json_data[str(key)] = value.to_dict()

        self._filename.parent.mkdir(exist_ok=True)
        with self._filename.open("w") as f:
            json.dump(json_data, f)

    def load(self) -> None:
        """This is called first when the synchronisation process is started."""
        try:
            with self._filename.open("r") as f:
                json_data = json.load(f)
        except FileNotFoundError:
            return

        for key, value in json_data.items():
            digest: str = value["digest"]
            plugin_name: str = value["plugin"]
            self._data[pathlib.Path(key)] = File(cached_digest=digest, plugin_name=plugin_name)

    def modify(self,
               path: pathlib.Path,
               plugin: syncplugin.AbstractSyncPlugin,
               local_digest_at_synctime: str) -> None:
        file = File(cached_digest=local_digest_at_synctime, plugin_name=plugin.NAME)
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

        if plugin.NAME != file.plugin_name:
            raise AssertionError(f"The cached plugin name '{file.plugin_name}' of the file "
                                 f"{local_full_path} doesn't match the plugin name "
                                 f"'{plugin.NAME}'.")

        remote_digest: str = plugin.create_remote_digest(remote_full_path)
        local_digest: str = plugin.create_local_digest(local_full_path)
        return self._compare_digests(remote_digest, local_digest, file.cached_digest)
