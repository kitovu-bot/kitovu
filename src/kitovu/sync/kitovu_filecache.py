"""FileCache keeps track of the state of the files, remotely and locally. It exists to determine if the local file
has been changed between two synchronisation processes and allows for a conflict handling accordingly."""

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


class File:
    def __init__(self, local_digest_at_synctime: str,
                 relative_path_with_filename: pathlib.PurePath,
                 plugin: syncplugin.AbstractSyncPlugin) -> None:
        self._cached_digest = local_digest_at_synctime
        self._relative_path_with_filename: pathlib.PurePath
        self._plugin = plugin
        self._remote_digest = ""
        self._local_digest = ""


class FileCache:
    def __init__(self, filename: str, path_to_json: pathlib.Path):
        self._FILECACHE = filename  # filecache.json
        self._path = path_to_json

    def write_filecache_to_jsonfile(self, file: typing.List[File]):
        """"Expects as argument all Files that need to be written to JSON."""
        filelist_to_json = json.dump(file)
        try:
            with pathlib.Path(self._path_to_json).joinpath(self._FILECACHE).open("a+") as f:
                # a+ = if it exsists, append; if not, create a new one
                f.write(filelist_to_json)
        except OSError as error:
            raise utils.UsageError(f"Could not write the file, {error}")

    def load_filecache_from_jsonfile(self) -> typing.List[File]:
        return json.load(pathlib.Path(self._path_to_json).joinpath(self._FILECACHE))


    def update_file_digest(self, file: File) -> None:
        # write File's cached_digest and path
        pass

    def discover_changes_in_file(self, file: File) -> int:

        # return ENUM: LOCAL; REMOTE; BOTH; NONE
        # queries Filecache, compare all this to decide what enum to return
        pass





