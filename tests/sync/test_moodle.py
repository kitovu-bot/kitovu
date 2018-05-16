import io
import typing
import urllib.parse
import pathlib

import attr
import keyring
import pytest

from kitovu import utils
from kitovu.sync.plugin import moodle
from kitovu.sync import syncing


@attr.s
class FakeStatResult:

    st_size: int = attr.ib()
    st_mtime: float = attr.ib()


@pytest.fixture
def plugin() -> moodle.MoodlePlugin:
    return moodle.MoodlePlugin()


@pytest.fixture
def moodle_assets_dir(assets_dir):
    return assets_dir / "moodle"


@pytest.fixture
def credentials():
    """Creates connection for test purposes, so as if we required the config."""
    keyring.set_password("kitovu-moodle", "https://moodle.hsr.ch/", "some_token")
    keyring.set_password("kitovu-moodle", "https://example.com/", "some_token")


def _patch_request(responses, wsfunction: str, body: str, status: int = 200, **kwargs: str) -> None:
    url = 'https://moodle.hsr.ch/webservice/rest/server.php'
    req_data: typing.Dict[str, str] = {
        'wstoken': 'some_token',
        'moodlewsrestformat': 'json',
        'wsfunction': wsfunction,
    }
    req_data.update(**kwargs)
    querystring = urllib.parse.urlencode(req_data)
    responses.add(responses.GET, f'{url}?{querystring}',
                  content_type="application/json", body=body, match_querystring=True, status=status)


@pytest.fixture
def patch_get_site_info(responses, moodle_assets_dir):
    body: str = (moodle_assets_dir / 'get_site_info.json').read_text(encoding='utf-8')
    _patch_request(responses, 'core_webservice_get_site_info', body=body)


@pytest.fixture
def patch_get_site_info_server_error(responses):
    _patch_request(responses, 'core_webservice_get_site_info', body="Kitovu-Error", status=500)


@pytest.fixture
def patch_get_users_courses(responses, moodle_assets_dir):
    body: str = (moodle_assets_dir / 'get_users_courses.json').read_text(encoding='utf-8')
    _patch_request(responses, 'core_enrol_get_users_courses', body=body, userid=4322)


@pytest.fixture
def patch_course_get_contents(responses, moodle_assets_dir):
    body: str = (moodle_assets_dir / 'course_wi2.json').read_text(encoding='utf-8')
    _patch_request(responses, 'core_course_get_contents', body=body, courseid=1172)


@pytest.fixture
def patch_course_get_contents_no_html(responses, moodle_assets_dir):
    body: str = (moodle_assets_dir / 'course_wi2.json').read_text(encoding='utf-8')
    body = body.replace('index.html', 'index')
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
def patch_get_wrong_wsfunction(responses):
    body: str = """
    {
        "errorcode": "invalidrecord",
        "exception": "dml_missing_record_exception",
        "message": "Datensatz kann nicht in der Datenbanktabelle external_functions gefunden werden"
    }
    """
    _patch_request(responses, 'core_webservice_get_site_info', body=body, wstoken="some_token")


@pytest.fixture
def patch_generic_moodle_error(responses):
    body: str = """
    {
        "errorcode": "alleskaputt",
        "exception": "alles_kaputt_error",
        "message": "Alles ist kaputt."
    }
    """
    _patch_request(responses, 'core_webservice_get_site_info', body=body, wstoken="some_token")


RETRIEVE_FILE_URL = ("https://moodle.hsr.ch/webservice/pluginfile.php/75099/mod_resource/content/7/"
                     "Gesch%C3%A4ftsprozessmanagement.pdf?forcedownload=1&token=some_token")


@pytest.fixture
def patch_retrieve_file(responses) -> None:
    responses.add(responses.GET, RETRIEVE_FILE_URL, content_type="application/octet-stream",
                  body="HELLO KITOVU", match_querystring=True)


@pytest.fixture
def patch_retrieve_file_server_error(responses) -> None:
    responses.add(responses.GET, RETRIEVE_FILE_URL, content_type="application/octet-stream",
                  body="HELLO KITOVU", match_querystring=True, status=500)


@pytest.fixture
def patch_retrieve_file_moodle_error(responses) -> None:
    body: str = """
    {
        "errorcode": "alleskaputt",
        "exception": "alles_kaputt_error",
        "message": "Alles ist kaputt."
    }
    """
    responses.add(responses.GET, RETRIEVE_FILE_URL, content_type="application/json",
                  body=body, match_querystring=True)


@pytest.fixture
def connect_and_configure_plugin(plugin, patch_get_site_info, credentials):
    plugin.configure({})
    plugin.connect()
    yield
    plugin.disconnect()


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
        with pytest.raises(utils.AuthenticationError):
            plugin.connect()

    def test_with_wrong_wsfunction(self, plugin, credentials, patch_get_wrong_wsfunction):
        plugin.configure({})
        with pytest.raises(utils.PluginOperationError):
            plugin.connect()

    def test_generic_moodle_exception(self, plugin, credentials, patch_generic_moodle_error):
        plugin.configure({})
        with pytest.raises(utils.PluginOperationError, match='Alles ist kaputt'):
            plugin.connect()

    def test_for_http_error_statuscode(self, plugin, credentials, patch_get_site_info_server_error):
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

    @pytest.mark.parametrize('list_courses_first', [True, False])
    @pytest.mark.parametrize('html_filename', [True, False])
    def test_list_remote_dir_of_course_files(self, list_courses_first, html_filename,
                                             plugin, connect_and_configure_plugin,
                                             patch_get_users_courses, request):
        patch = 'patch_course_get_contents'
        if not html_filename:
            patch += '_no_html'
        request.getfixturevalue(patch)

        if list_courses_first:
            list(plugin.list_path(pathlib.PurePath("/")))
        course_contents: typing.Iterable[pathlib.PurePath] = list(
            plugin.list_path(pathlib.PurePath("Wirtschaftsinformatik 2 FS2018")))
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

    @pytest.mark.parametrize('filename', ['foo', 'foo.png', 'foo.html'])
    def test_create_local_digest(self, plugin, monkeypatch, filename, temppath):
        testfile = temppath / filename
        text = 'hello kitovu'
        testfile.write_text(text)

        mtime = 13371337.4242
        monkeypatch.setattr(pathlib.Path, 'stat', lambda _self:
                            FakeStatResult(st_size=len(text), st_mtime=mtime))

        plugin.create_local_digest(testfile)
        expected_size = 0 if filename == 'foo.html' else len(text)

        assert plugin.create_local_digest(testfile) == f'{expected_size}-13371337'

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

    def test_list_path_with_wrong_remote_dir(self, plugin, connect_and_configure_plugin, patch_get_users_courses):
        """Check if configuration has been written with correct remote-dir.

        There's a short name and a full name for each course, students need to choose the full name for the config.
        list_path uses list_course which asks for full name, we give the wrong short name. This test covers issue EPJ-92.

        Cf. this bogus config that is incorrectly configured:

        root-dir: ./testkitovu
        connections:
            - name: mytest-moodle
              plugin: moodle
        subjects:
            - name: Wi2
              sources:
                - connection: mytest-moodle
                  remote-dir: "M_WI2_FS2018" <== wrong name
        """
        wrong_remote_dir: str = "M_WI2_FS2018"
        with pytest.raises(utils.PluginOperationError):
            list(plugin.list_path(pathlib.PurePath(wrong_remote_dir)))

    def test_retrieve_file(self, plugin, connect_and_configure_plugin,
                           patch_get_users_courses, patch_course_get_contents, patch_retrieve_file):
        list(plugin.list_path(pathlib.PurePath("Wirtschaftsinformatik 2 FS2018")))
        remote_full_path = pathlib.PurePath('Wirtschaftsinformatik 2 FS2018/02 - Geschäftsprozessmanagement/'
                                            'Geschäftsprozessmanagement/Geschäftsprozessmanagement.pdf')
        fileobj = io.BytesIO()
        assert plugin.retrieve_file(remote_full_path, fileobj) == 1520803270
        assert fileobj.getvalue() == b"HELLO KITOVU"

    def test_retrieve_file_server_error(self, plugin, connect_and_configure_plugin,
                                        patch_get_users_courses, patch_course_get_contents,
                                        patch_retrieve_file_server_error):
        list(plugin.list_path(pathlib.PurePath("Wirtschaftsinformatik 2 FS2018")))
        remote_full_path = pathlib.PurePath('Wirtschaftsinformatik 2 FS2018/02 - Geschäftsprozessmanagement/'
                                            'Geschäftsprozessmanagement/Geschäftsprozessmanagement.pdf')
        fileobj = io.BytesIO()

        with pytest.raises(utils.PluginOperationError):
            plugin.retrieve_file(remote_full_path, fileobj)

    def test_retrieve_file_moodle_error(self, plugin, connect_and_configure_plugin,
                                        patch_get_users_courses, patch_course_get_contents,
                                        patch_retrieve_file_moodle_error):
        list(plugin.list_path(pathlib.PurePath("Wirtschaftsinformatik 2 FS2018")))
        remote_full_path = pathlib.PurePath('Wirtschaftsinformatik 2 FS2018/02 - Geschäftsprozessmanagement/'
                                            'Geschäftsprozessmanagement/Geschäftsprozessmanagement.pdf')
        fileobj = io.BytesIO()

        with pytest.raises(utils.PluginOperationError):
            plugin.retrieve_file(remote_full_path, fileobj)
