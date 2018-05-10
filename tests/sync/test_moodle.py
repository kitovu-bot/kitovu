import io
import typing
import urllib.parse
import pathlib

import keyring
import pytest

from kitovu import utils
from kitovu.sync.plugin import moodle
from kitovu.sync import syncing


@pytest.fixture
def plugin() -> moodle.MoodlePlugin:
    return moodle.MoodlePlugin()


@pytest.fixture
def credentials():
    """Creates connection for test purposes, so as if we required the config."""
    keyring.set_password("kitovu-moodle", "https://moodle.hsr.ch/", "some_token")
    keyring.set_password("kitovu-moodle", "https://example.com/", "some_token")


def _patch_request(responses, wsfunction: str, body: str, **kwargs: str) -> None:
    url = 'https://moodle.hsr.ch/webservice/rest/server.php'
    req_data: typing.Dict[str, str] = {
        'wstoken': 'some_token',
        'moodlewsrestformat': 'json',
        'wsfunction': wsfunction,
    }
    req_data.update(**kwargs)
    querystring = urllib.parse.urlencode(req_data)
    responses.add(responses.GET, f'{url}?{querystring}',
                  content_type="application/json", body=body, match_querystring=True)


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
def connect_and_configure_plugin(plugin, patch_get_site_info, credentials):
    plugin.configure({})
    plugin.connect()


@pytest.fixture
def patch_retrieve_file(responses) -> None:
    url = ("https://moodle.hsr.ch/webservice/pluginfile.php/75099/mod_resource/content/7/" 
           "Gesch%C3%A4ftsprozessmanagement.pdf?forcedownload=1&token=some_token")
    responses.add(responses.GET, url, content_type="application/octet-stream",
                  body="HELLO KITOVU", match_querystring=True)


@pytest.mark.parametrize("info, expected", [
    ({}, "https://moodle.hsr.ch/"),
    ({"url": "https://example.com/"}, "https://example.com/"),
    ({"url": "https://example.com"}, "https://example.com/"),
])
def test_configure(plugin, credentials, info, expected):
    plugin.configure(info)
    assert plugin._url == expected
    assert plugin._token == "some_token"


class TestConnect:

    def test_connect(self, plugin, patch_get_site_info, credentials):
        plugin.configure({})
        plugin.connect()
        assert plugin._user_id == 4322

    def test_connect_with_wrong_token(self, plugin, patch_get_site_info_wrong_token):
        keyring.set_password("kitovu-moodle", "https://moodle.hsr.ch/", "wrong_token")
        plugin.configure({})
        with pytest.raises(utils.PluginOperationError):
            plugin.connect()


class TestValidations:

    def test_validate_config(self, temppath):
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

    def test_config_with_url(self, temppath):
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
        root-dir: ./testkitovu
        connections:
            - name: mytest-moodle
              plugin: moodle
              url: https://example.com
        subjects:
            - name: Wi2
              sources:
                - connection: mytest-moodle
                  remote-dir: "Wirtschaftsinformatik 2 FS2018"
        """)
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
        with pytest.raises(utils.InvalidSettingsError):
            syncing.validate_config(config_yml)


class TestWithConnectedPlugin:

    def test_list_remote_dir_of_courses(self, plugin, connect_and_configure_plugin, patch_get_users_courses):
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

    def test_list_remote_dir_of_course_files(self, plugin, connect_and_configure_plugin,
                                             patch_get_users_courses, patch_course_get_contents):
        course_contents: typing.Iterable[pathlib.PurePath] = \
            list(plugin.list_path(pathlib.PurePath("Wirtschaftsinformatik 2 FS2018")))
        expected_contents = [
            pathlib.PurePath('Wirtschaftsinformatik 2 FS2018/02 - Geschäftsprozessmanagement/'
                             'Geschäftsprozessmanagement/Geschäftsprozessmanagement.pdf'),
            pathlib.PurePath('Wirtschaftsinformatik 2 FS2018/02 - Geschäftsprozessmanagement/'
                             'Vielerlei Konzepte im Geschäftsprozessmanagement/index.html'),
            pathlib.PurePath('Wirtschaftsinformatik 2 FS2018/02 - Geschäftsprozessmanagement/'
                             'Lösung Aufgabe 1/index.html'),
            pathlib.PurePath('Wirtschaftsinformatik 2 FS2018/03 - BPMN1 - Introduction to Business Process Management/'
                             '1. Introduction to Business Process Management/'
                             '1. Introduction to Business Process Management.pdf'),
            pathlib.PurePath('Wirtschaftsinformatik 2 FS2018/03 - BPMN1 - Introduction to Business Process Management/'
                             'Solution Modeling Task 1 - Loan application at Wall Street Oasis (WSO) bank/'
                             'Modeling Task 1 - Loan application at Wall Street Oasis (WSO) bank.PNG')
        ]
        assert course_contents == expected_contents

    def test_create_remote_digest(self, plugin, connect_and_configure_plugin,
                                  patch_get_users_courses, patch_course_get_contents):
        course_contents: typing.Iterable[pathlib.PurePath] = list(
            plugin.list_path(pathlib.PurePath("Wirtschaftsinformatik 2 FS2018")))
        remote_digests = []
        check_digests = [
            '4267895-1520803270',
            '0-1487838705',
            '0-1520427130',
            '2119487-1490374823',
            '44733-1396277827'
        ]
        for item in course_contents:
            remote_digests.append(plugin.create_remote_digest(item))
        assert remote_digests == check_digests

    def list_path_with_wrong_remote_dir(self, temppath):
        """Checks if configuration has been written with correct remote-dir.

        There's a short name and a full name for each course, students need to choose the full name for the config.
        list_path uses list_course which asks for full name, we give the wrong short name.
        """
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

    def test_retrieve_file(self, plugin, connect_and_configure_plugin,
                           patch_get_users_courses, patch_course_get_contents, patch_retrieve_file):
        list(plugin.list_path(pathlib.PurePath("Wirtschaftsinformatik 2 FS2018")))
        remote_full_path = pathlib.PurePath('Wirtschaftsinformatik 2 FS2018/02 - Geschäftsprozessmanagement/'
                                            'Geschäftsprozessmanagement/Geschäftsprozessmanagement.pdf')
        fileobj = io.BytesIO()
        assert plugin.retrieve_file(remote_full_path, fileobj) == 1520803270
        assert fileobj.getvalue() == b"HELLO KITOVU"
