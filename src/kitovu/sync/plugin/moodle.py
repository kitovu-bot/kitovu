"""Plugin to talk to Moodle instances."""

import typing
import pathlib
import os

import requests

from kitovu import utils
from kitovu.sync import syncplugin


JsonType = typing.Dict[str, typing.Any]


class _MoodleFile:

    def __init__(self, url: str, size: int, changed_at: int) -> None:
        self.url: str = url
        self.size: int = size
        self.changed_at: int = changed_at


class MoodlePlugin(syncplugin.AbstractSyncPlugin):

    """A plugin which talks to Moodle using its Web Services."""

    def __init__(self) -> None:
        self._url: str = ''
        self._user_id: int = -1
        self._token: str = ''
        self._courses: typing.Dict[str, int] = {}
        self._files: typing.Dict[pathlib.PurePath, _MoodleFile] = {}

    def _request(self, func: str, **kwargs: str) -> typing.Any:
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
        assert 'error' not in data, data
        return data

    def configure(self, info: JsonType) -> None:
        self._url = info.get('url', 'https://moodle.hsr.ch/')
        if not self._url.endswith('/'):
            self._url += '/'

        self._token = utils.get_password('moodle', self._url)

    def connect(self) -> None:
        # Get our own user ID
        site_info: JsonType = self._request('core_webservice_get_site_info')
        self._user_id: int = site_info['userid']

    def disconnect(self) -> None:
        pass

    def _create_digest(self, size: int, changed_at: int) -> str:
        return f'{size}-{changed_at}'

    def create_local_digest(self, path: pathlib.Path) -> str:
        stats = path.stat()
        print(stats)
        return self._create_digest(stats.st_size, int(stats.st_mtime))

    def create_remote_digest(self, path: pathlib.PurePath) -> str:
        moodle_file = self._files[path]
        return self._create_digest(moodle_file.size, moodle_file.changed_at)

    def _list_courses(self) -> typing.Iterable[str]:
        courses: typing.List[JsonType] = self._request('core_enrol_get_users_courses',
                                                       userid=str(self._user_id))
        for course in courses:
            self._courses[course['fullname']] = int(course['id'])
        return list(self._courses)

    def _list_files(self, course_path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        course = str(course_path)
        if not self._courses:
            self._list_courses()

        course_id = self._courses[course]
        lessons: typing.List[JsonType] = self._request('core_course_get_contents',
                                                       courseid=str(course_id))

        for section in lessons:
            section_path = course_path / section['name']
            for module in section['modules']:
                module_path = section_path / module['name']
                for elem in module.get('contents', []):
                    if 'mimetype' not in elem:
                        continue
                    local_path = module_path / elem['filename']
                    self._files[local_path] = _MoodleFile(elem['fileurl'],
                                                          elem['filesize'],
                                                          elem['timemodified'])
                    yield local_path

    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        """Get a list of all courses, or files in a course."""
        if path == pathlib.PurePath('/'):
            for course in self._list_courses():
                yield pathlib.PurePath(course)
        else:
            # FIXME
            for filename in self._list_files(path):
                yield filename

    def retrieve_file(self, path: pathlib.PurePath, fileobj: typing.IO[bytes],
                      local_path: pathlib.Path) -> None:
        moodle_file = self._files[path]
        fileurl = moodle_file.url

        req = requests.get(fileurl, {'token': self._token})
        assert req.status_code == 200, req  # FIXME
        if 'json' in req.headers['content-type']:
            data = req.json()
            assert 'exception' not in data, data
            assert 'error' not in data, data
        for chunk in req:
            fileobj.write(chunk)

        fileobj.flush()
        os.utime(local_path, (local_path.stat().st_atime, moodle_file.changed_at))
