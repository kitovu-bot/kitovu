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
    # first param: received in syncing.py:  local_digest = plugin.create_local_digest(output)
    # second param: received in syncing.py: output = pathlib.Path(outputpath / item.relative_to(path))
    # the second param identifies a File uniquely
    def __init__(self, local_digest_at_synctime: str, relative_path_with_filename: pathlib.PurePath) -> None:
        self.cached_digest: str = local_digest_at_synctime
        self.relative_path_with_filename: pathlib.PurePath = relative_path_with_filename
        self.local_digest: str = ""
        self.remote_digest: str = ""

    # saves local digest, file name + path, e.g  "/EPJ/2018/Gruppen/erklaerung.txt"
    # create on the fly: remote digest, local digest (from the downloaded file)

    # methods:
    # 1. discover what has changed on which side. ENUM: LOCAL; REMOTE; BOTH; NONE
    # 2. update_Digests

    # FileCache: gets all file-objects, out of which it writes the JSON-File

    def set_local_digest(self, ld: str) -> None:
        self.local_digest = ld

    def set_remote_digest(self, rd: str) -> None:
        self.remote_digest = rd


class FileCache:

    def discover_changes_in_file(self, file: File) -> int:
        # return ENUM: LOCAL; REMOTE; BOTH; NONE
        # queries Filecache, compare all this to decide what enum to return
        pass

    def update_file_digest(self, file: File) -> None:
        # write File's cached_digest and path
        pass

    def write_file_to_filecache(self, file: File):
        pass

    def retrieve_file_from_filecache(self, path: pathlib.PurePath):
        pass

