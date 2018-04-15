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
        file_properties = {"path": relative_path_with_filename,
                           "plugin": plugin,
                           "digests": {
                                "cached digest": local_digest_at_synctime,
                                }
                           }


class FileCache:
    FILECACHE: str = "filecache.json"

    def write_file_to_filecache(self, file: File):
        file_to_json = json.dumps(file)
        try:
            with self.FILECACHE.open("a+") as f:  # a+ = if it exsists, append; if not, create a new one
                f.write(file_to_json)
        except OSError as error:
            raise utils.UsageError(f"Could not write the file, {error}")

    def retrieve_jsonfile_from_filecache(self, file: File) -> File:
        try:
            with self.FILECACHE.open("r") as f:
                json_to_file = json.load(f.read())
                file = json_to_file["path"]

        except FileNotFoundError as error:
            raise utils.UsageError(f"File not found, {error}")

    def update_file_digest(self, file: File) -> None:
        # write File's cached_digest and path
        pass

    def discover_changes_in_file(self, file: File) -> int:

        # return ENUM: LOCAL; REMOTE; BOTH; NONE
        # queries Filecache, compare all this to decide what enum to return
        pass





