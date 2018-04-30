import pytest
import pathlib
import json

from kitovu.sync import filecache
from kitovu.sync.plugin.smb import SmbPlugin


@pytest.fixture
def cache(temppath) -> filecache.FileCache:
    return filecache.FileCache(temppath / "test_filecache.json")


class TestFile:

    def test_to_dict(self, temppath):
        file = filecache.File("this_is_a_digest", "dummyplugin")
        assert file.to_dict() == {"plugin": "dummyplugin", "digest": "this_is_a_digest"}


class TestLoadWrite:

    def test_write(self, temppath, cache, plugin):
        cache.modify(temppath / "testfile1.txt", plugin, "digest1")
        cache.modify(temppath / "testfile2.pdf", plugin, "digest2")
        cache.modify(temppath / "testfile3.png", plugin, "digest3")
        cache.write()
        with cache._filename.open("r") as f:
            json_data = json.load(f)
        assert json_data == {str(temppath / "testfile1.txt"): {"digest": "digest1", "plugin": "dummyplugin"},
                             str(temppath / "testfile2.pdf"): {"digest": "digest2", "plugin": "dummyplugin"},
                             str(temppath / "testfile3.png"): {"digest": "digest3", "plugin": "dummyplugin"}}

    def test_load(self, temppath, cache, plugin):
        cache.modify(temppath / "testfile4.txt", plugin, "digest4")
        cache.modify(temppath / "testfile5.pdf", plugin, "digest5")
        cache.modify(temppath / "testfile6.png", plugin, "digest6")
        cache.write()
        cache.load()
        assert cache._data == {temppath / "testfile4.txt": filecache.File(cached_digest="digest4",
                                                                          plugin_name="dummyplugin"),
                               temppath / "testfile5.pdf": filecache.File(cached_digest="digest5",
                                                                          plugin_name="dummyplugin"),
                               temppath / "testfile6.png": filecache.File(cached_digest="digest6",
                                                                          plugin_name="dummyplugin")}

    def test_filecache_not_found(self, temppath, cache, plugin):
        cache.load()
        assert not cache._data


class TestChange:

    def test_modify(self, temppath, plugin, cache):
        cache.modify(temppath / "testfile1.txt", plugin, "digest1")
        testfile = filecache.File(cached_digest="digest1", plugin_name="dummyplugin")
        assert cache._data[temppath / "testfile1.txt"] == testfile

    def test_not_matching_pluginname(self, temppath, plugin, cache):
        local = temppath / "local_dir/test/example1.txt"
        local.parent.mkdir(parents=True)
        local.touch()
        remote = pathlib.PurePath("remote_dir/test/example1.txt")

        cache.modify(local, plugin, plugin.remote_digests[remote])

        wrongplugin = SmbPlugin()
        with pytest.raises(AssertionError):
            cache.discover_changes(local, remote, wrongplugin)


class TestFileState:

    def test_file_is_new(self, temppath, plugin, cache):
        local = temppath / "testfile1.txt"
        remote = pathlib.PurePath(temppath) / "testfile1.txt"
        assert cache.discover_changes(local, remote, plugin) == filecache.FileState.NEW

    def test_remote_file_changed(self, temppath, plugin, cache):
        plugin.connect()
        local = temppath / "local_dir/test/example4.txt"
        local.parent.mkdir(parents=True)
        local.touch()
        remote = pathlib.PurePath("remote_dir/test/example4.txt")

        cache.modify(local, plugin, plugin.remote_digests[remote])
        plugin.remote_digests[remote] = "44"
        assert cache.discover_changes(local, remote, plugin) == filecache.FileState.REMOTE_CHANGED

    def test_file_not_changed(self, temppath, plugin, cache):
        plugin.connect()
        local = temppath / "local_dir/test/example1.txt"
        local.parent.mkdir(parents=True)
        local.touch()
        remote = pathlib.PurePath("remote_dir/test/example1.txt")

        cache.modify(local, plugin, plugin.remote_digests[remote])
        assert cache.discover_changes(local, remote, plugin) == filecache.FileState.NO_CHANGES

    def test_local_file_changed(self, temppath, plugin, cache):
        plugin.connect()
        local = temppath / "local_dir/test/example2.txt"
        local.parent.mkdir(parents=True)
        local.touch()

        remote = pathlib.PurePath("remote_dir/test/example2.txt")
        cache.modify(local, plugin, plugin.remote_digests[remote])
        plugin.local_digests[local] = "22"
        assert cache.discover_changes(local, remote, plugin) == filecache.FileState.LOCAL_CHANGED

    def test_remote_and_local_file_changed(self, temppath, plugin, cache):
        plugin.connect()
        local = temppath / "local_dir/test/example3.txt"
        local.parent.mkdir(parents=True)
        local.touch()

        remote = pathlib.PurePath("remote_dir/test/example3.txt")
        cache.modify(local, plugin, plugin.remote_digests[remote])
        plugin.local_digests[local] = "33"
        plugin.remote_digests[remote] = "99"
        assert cache.discover_changes(local, remote, plugin) == filecache.FileState.BOTH_CHANGED
