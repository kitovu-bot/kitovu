import pathlib
import urllib.parse
import typing


import keyring
import pytest

from helpers import reporter
from kitovu.sync import syncing
from kitovu import utils
from kitovu.sync.plugin import moodle


@pytest.fixture
def plugin() -> moodle.MoodlePlugin:
    return moodle.MoodlePlugin(reporter.TestReporter())


@pytest.fixture
def assets_dir() -> pathlib.Path:
    # FIXME find this in a better way
    return pathlib.Path('./tests/assets')


@pytest.fixture
def patch_get_site_info(responses, assets_dir):
    body: str = (assets_dir / 'siteinfo.json').read_text()
    _patch_request(responses, 'core_webservice_get_site_info', body=body)


@pytest.fixture
def credentials():
    """Creates connection for test purposes, so as if we required the config."""
    keyring.set_password("kitovu-moodle", "https://moodle.hsr.ch/", "some_token")


def _patch_request(responses, wsfunction: str, body: str, **kwargs: str) -> None:
    url = 'https://moodle.hsr.ch/webservice/rest/server.php'
    req_data: typing.Dict[str, str] = {
        'wstoken': 'some_token',
        'moodlewsrestformat': 'json',
        'wsfunction': wsfunction,
    }
    req_data.update(**kwargs)
    querystring = urllib.parse.urlencode(req_data)
    responses.add(responses.GET, f'{url}?{querystring}', body=body, match_querystring=True)


class TestConnect:

    def test_connect(self, plugin, patch_get_site_info, credentials):
        plugin.configure({})
        plugin.connect()
        assert plugin._user_id == 4322

    def test_connect_with_custom_options(self):
        pass

    def test_connect_with_hsr_config(self):
        pass


class TestValidations:

    def test_config_with_all_available_fields(self):
        pass

    def test_config_with_minimum_required_fields(self):
        pass

    def test_config_with_max_required_fields(self):
        pass

    def test_config_with_unexpected_fields(self):
        pass


class TestWithConnectedPlugin:

    def test_create_remote_digest(self):
        pass

    def test_disconnect(self):
        pass

    def test_list_path(self):
        pass
