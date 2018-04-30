import pytest
import pathlib
import json

from kitovu.sync import filecache


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


class TestChange:

    def test_modify(self, temppath, plugin, cache):
        cache.modify(temppath / "testfile1.txt", plugin, "digest1")
        testfile = filecache.File(cached_digest="digest1", plugin_name="dummyplugin")
        assert cache._data[temppath / "testfile1.txt"] == testfile

    def test_not_matching_pluginname(self, temppath, plugin, cache):
        cache.modify(temppath / "testfile2.pdf", plugin, "digest2")
        testfile = filecache.File(cached_digest="digest2", plugin_name="smb")
        with pytest.raises(AssertionError):
            assert cache._data[temppath / "testfile2.pdf"] == testfile


class TestFileState:

    def test_file_is_new(self, temppath, plugin, cache):
        local = temppath / "testfile1.txt"
        remote = pathlib.PurePath(temppath) / "testfile1.txt"
        assert cache.discover_changes(local, remote, plugin) == filecache.FileState.NEW

    def test_remote_file_changed(self, temppath, plugin, cache):
        local = pathlib.Path("dir/test/example1.txt")
        remote = pathlib.PurePath("dir/test/example1.txt")

        cache.modify(temppath / "dir/test/example1.txt", plugin, plugin.remote_digests[pathlib.PurePath("dir/test/example1.txt")])
        plugin.remote_digests[pathlib.PurePath("dir/test/example1.txt")] = "11"
        assert cache.discover_changes(local, remote, plugin) == filecache.FileState.REMOTE_CHANGED

    def test_file_not_changed(self, temppath, plugin, cache):
        pass

    def test_local_file_changed(self, temppath, plugin, cache):
        pass

    def test_remote_and_local_file_changed(self, temppath, plugin, cache):
        pass
