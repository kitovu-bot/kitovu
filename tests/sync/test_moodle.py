import pathlib
import urllib.parse
import typing


import keyring
import pytest

from helpers import reporter
from kitovu.sync.plugin import moodle


@pytest.fixture
def plugin() -> moodle.MoodlePlugin:
    return moodle.MoodlePlugin(reporter.TestReporter())


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


@pytest.fixture
def patch_get_site_info(responses, assets_dir):
    body: str = (assets_dir / 'get_site_info.json').read_text()
    _patch_request(responses, 'core_webservice_get_site_info', body=body)


@pytest.fixture
def patch_get_users_courses(responses, assets_dir):
    body: str = (assets_dir / 'get_users_courses.json').read_text()
    _patch_request(responses, 'core_enrol_get_users_courses', body=body, userid=4322)


@pytest.fixture
def course_get_contents(responses, assets_dir, filename: str):
    body: str = (assets_dir / filename).read_text()


class TestConnect:

    def test_connect(self, plugin, patch_get_site_info, credentials):
        plugin.configure({})
        plugin.connect()
        assert plugin._user_id == 4322

    def test_connect_with_wrong_token(self):
        #check what comes back with http
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

    def test_retrieve_file(self):
        pass
