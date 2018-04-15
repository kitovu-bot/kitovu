"""FileCache keeps track of the state of the files, remotely and locally. It exists to determine if the local file
has been changed between two synchronisation processes and allows for a conflict handling accordingly."""

from enum import Enum
import json
import pathlib
import typing

from kitovu.sync import syncplugin

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
                           "cached digest": local_digest_at_synctime,
                           "local digest": "",
                           "remote digest": ""}


class FileCache:

    def write_file_to_filecache(self, file: File):
        json.dumps(file)

    def retrieve_file_from_filecache(self, path: pathlib.PurePath):
        pass

    def discover_changes_in_file(self, file: File) -> int:
        # return ENUM: LOCAL; REMOTE; BOTH; NONE
        # queries Filecache, compare all this to decide what enum to return
        pass

    def update_file_digest(self, file: File) -> None:
        # write File's cached_digest and path
        pass

