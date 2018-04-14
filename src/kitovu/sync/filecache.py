"""FileCache keeps track of the state of the files, remotely and locally. It exists to determine if the local file
has been changed between two synchronisation processes and allows for a conflict handling accordingly."""

import json
import pathlib
import typing

from kitovu import utils

# FIXME sync-process:
# every time we sync something, the FileCache gets read, upon which kitovu decides what needs to be downloaded.
# The files get downloaded, for each file, the FileCache gets updated for the files that were synchronised.


class File:

    def __init__(self, local_digest_at_synctime: str, relative_path_with_filename: pathlib.PurePath) -> None:
        self.cached_digest = local_digest_at_synctime
        self.relative_path_with_filename

# saves local digest, file name + path, e.g  "/EPJ/2018/Gruppen/erklaerung.txt"
# create on the fly: remote digest, local digest (from the downloaded file)

# methods:
# 1. discover what has changed on which side. ENUM: LOCAL; REMOTE; BOTH; NONE
# 2. update_Digests

# FileCache: gets all file-objects, out of which it writes the JSON-File


def discover_changes_in_file():
    # return ENUM: LOCAL; REMOTE; BOTH; NONE
    # plugin.create_remote_digest(self, path: pathlib.PurePath)
    # plugin create_local_digest(self, path: pathlib.Path) -> str:
    # File's cached_digest and path
    # compare all this to decide what enum to return
    pass


def update_file_digest(File): # or update_digests()
    # write File's cached_digest and path
    pass


def get_file(path):
    pass


