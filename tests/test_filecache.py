import pathlib
import typing

import pytest


from tests.helpers import dummyplugin
from kitovu.sync import filecache


@pytest.fixture()
def plugin() -> dummyplugin.DummyPlugin():
    return dummyplugin


@pytest.fixture()
def filecache() -> filecache.FileCache():
    return filecache.FileCache


@pytest.fixture()
def file() -> filecache.File():
    return filecache.file


def test_if_dictionary_is_returned():
    pass


def test_filecache_write():
    pass


def test_filecach_modify():
    pass


def test_filecache_discover_changers():
    pass


def test_file_is_new():
    pass


def test_remote_file_changed():
    pass

def test_file_not_changed():
    pass

def test_local_file_changed():
    pass

def test_remote_and_local_file_changed():
    pass


