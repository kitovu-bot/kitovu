"""Plugin to talk to Moodle instances."""

import typing
import pathlib

import requests

from kitovu import config
from kitovu.sync import syncplugin


class MoodlePlugin(syncplugin.AbstractSyncPlugin):

    """A plugin which talks to Moodle using its Web Services."""

    def __init__(self) -> None:
        self._url: str = None
        self._user_id: int = None
        self._courses: typing.Dict[str, int] = {}
        self._files: typing.Dict[str, typing.Dict[str, str]] = {}

    def _request(self, func, **kwargs) -> typing.Any:
        url = self._url + 'webservice/rest/server.php'
        data = {
            'wstoken': self._token,
            'moodlewsrestformat': 'json',
            'wsfunction': func,
        }
        data.update(**kwargs)
        req = requests.get(url, data)
        assert req.status_code == 200, req  # FIXME
        data = req.json()
        assert 'exception' not in data, data
        return data

    def configure(self, info: typing.Dict[str, typing.Any]) -> None:
        self._url = info.get('url', 'https://moodle.hsr.ch/')
        if not self._url.endswith('/'):
            self._url += '/'

        self._token = config.get_password('moodle', self._url)

    def connect(self) -> None:
        # Get our own user ID
        site_info: typing.Dict[str, typing.Any] = self._request('core_webservice_get_site_info')
        self._user_id: int = site_info['userid']

    def disconnect(self) -> None:
        pass

    def create_local_digest(self, path: pathlib.Path) -> str:
        """FIXME"""
        return ''

    def create_remote_digest(self, path: pathlib.PurePath) -> str:
        """FIXME"""
        return ''

    def _list_courses(self) -> typing.Iterable[str]:
        courses = self._request('core_enrol_get_users_courses', userid=self._user_id)
        for course in courses:
            self._courses[course['fullname']] = course['id']
            self._files[course['fullname']] = {}
        return list(self._courses)

    def _list_files(self, course: str) -> typing.Iterable[str]:
        if not self._courses:
            self._list_courses()

        course_id = self._courses[course]
        lessons = self._request('core_course_get_contents', courseid=course_id)

        for section in lessons:
            for module in section['modules']:
                for elem in module.get('contents', []):
                    if 'mimetype' not in elem:
                        continue
                    self._files[course][elem['filename']] = elem['fileurl']
                    yield elem['filename']

    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        """Get a list of all courses, or files in a course."""
        if path == pathlib.PurePath('/'):
            for course in self._list_courses():
                yield pathlib.PurePath(course)
        else:
            # FIXME
            course = str(path)
            for filename in self._list_files(course):
                yield path / filename

    def retrieve_file(self, path: pathlib.PurePath, fileobj: typing.IO[bytes]) -> None:
        assert len(path.parts) == 2, path
        course = path.parts[0]
        filename = path.parts[1]
        fileurl = self._files[course][filename]

        req = requests.get(fileurl, data={'token': self._token})
        assert req.status_code == 200, req  # FIXME
        for chunk in req:
            fileobj.write(chunk)
