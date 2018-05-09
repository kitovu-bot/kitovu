import typing
import urllib.parse
import pathlib

import keyring
import pytest


import kitovu.utils
from kitovu.sync.plugin import moodle
from kitovu.sync import syncing


@pytest.fixture
def plugin() -> moodle.MoodlePlugin:
    return moodle.MoodlePlugin()


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
def patch_course_get_contents(responses, assets_dir):
    body: str = (assets_dir / 'course_wi2.json').read_text()
    _patch_request(responses, 'core_course_get_contents', body=body, courseid=1172)


@pytest.fixture
def patch_get_site_info_wrong_token(responses):
    body: str = """
    {
    "errorcode": "invalidtoken", 
    "exception": "moodle_exception", 
    "message": "Ungültiges Token - Token wurde nicht gefunden"
    }
    """
    _patch_request(responses, 'core_webservice_get_site_info', body=body, wstoken="wrong_token")


@pytest.fixture
def patch_connect_and_configure_plugin(plugin, patch_get_site_info, credentials):
    plugin.configure({})
    plugin.connect()


class TestConnect:

    def test_connect(self, plugin, patch_get_site_info, credentials):
        plugin.configure({})
        plugin.connect()
        assert plugin._user_id == 4322

    def test_connect_with_wrong_token(self, plugin, patch_get_site_info_wrong_token):
        keyring.set_password("kitovu-moodle", "https://moodle.hsr.ch/", "wrong_token")
        plugin.configure({})
        with pytest.raises(AssertionError):
            plugin.connect()


class TestValidations:

    def test_config_with_url(self, temppath):
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
        root-dir: ./testkitovu
        connections:
            - name: mytest-moodle
              plugin: moodle
        subjects:
            - name: Wi2
              sources:
                - connection: mytest-moodle
                  remote-dir: "Wirtschaftsinformatik 2 FS2018"             
        """)
        syncing.validate_config(config_yml)

    def test_with_empty_config(self, temppath):
        config_yml = temppath / 'config.yml'
        config_yml.write_text("")
        with pytest.raises(kitovu.utils.InvalidSettingsError):
            syncing.validate_config(config_yml)

    def test_config_with_unexpected_connection_fields(self, temppath):
        # bogus setting: connection: 42
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
                root-dir: ./testkitovu
                connections:
                    - name: mytest-moodle
                      plugin: moodle
                      connection: 42
                subjects:
                    - name: Wi2
                      sources:
                        - connection: mytest-moodle
                          remote-dir: "Wirtschaftsinformatik 2 FS2018"             
                """)
        with pytest.raises(kitovu.utils.InvalidSettingsError):
            syncing.validate_config(config_yml)


class TestWithConnectedPlugin:

    def test_list_remote_dir_of_courses(self, plugin, patch_connect_and_configure_plugin, patch_get_users_courses):
        courses: typing.Iterable[pathlib.PurePath] = list(plugin.list_path(pathlib.PurePath("/")))
        expected_courses = [
            pathlib.PurePath('Wirtschaftsinformatik 2 FS2018'),
            pathlib.PurePath('Software-Engineering 1 HS2016'),
            pathlib.PurePath('Betriebssysteme 2 FS2016'),
            pathlib.PurePath('Datenbanksysteme 1 HS2015'),
            pathlib.PurePath('Wahrscheinlichkeitsrechnung und Statistik'),
            pathlib.PurePath('Moodle Support'),
        ]
        assert courses == expected_courses

    def test_list_remote_dir_of_course_files(self, plugin, patch_connect_and_configure_plugin, patch_get_users_courses, patch_course_get_contents):
        course_contents: typing.Iterable[pathlib.PurePath] = list(plugin.list_path(pathlib.PurePath("Wirtschaftsinformatik 2 FS2018")))
        expected_contents = []
        assert course_contents == expected_contents

    def test_create_remote_digest(self, plugin, patch_course_get_contents):
        pass

    def list_path_with_wrong_remote_dir(self, temppath):
        """Checks if configuration has been written with correct remote-dir.
        There's a short name and a full name for each course, students need to choose the full name for the config.
        """
        # list_path uses list_course which asks for fullname, we give shortname
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
        root-dir: ./testkitovu
        connections:
            - name: mytest-moodle
              plugin: moodle
        subjects:
            - name: Wi2
              sources:
                - connection: mytest-moodle
                  remote-dir: "M_WI2_FS2018"             
        """)
        with pytest.raises(KeyError):
            plugin.list_path()


    def test_retrieve_file(self):
        pass
