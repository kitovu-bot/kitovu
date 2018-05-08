"""Plugin to talk to Moodle instances."""

import os
import typing
import pathlib
import logging

import attr
import requests

from kitovu import utils
from kitovu.sync import syncplugin


logger: logging.Logger = logging.getLogger(__name__)
JsonType = typing.Dict[str, typing.Any]


@attr.s
class _MoodleFile:

    url: str = attr.ib()
    size: int = attr.ib()
    changed_at: int = attr.ib()


class MoodlePlugin(syncplugin.AbstractSyncPlugin):

    """A plugin which talks to Moodle using its Web Services."""

    NAME = 'moodle'

    def __init__(self, reporter: utils.AbstractReporter) -> None:
        super().__init__(reporter)
        self._url: str = ''
        self._user_id: int = -1
        self._token: str = ''
        self._courses: typing.Dict[str, int] = {}
        self._files: typing.Dict[pathlib.PurePath, _MoodleFile] = {}

    def _request(self, func: str, **kwargs: str) -> typing.Any:
        url = self._url + 'webservice/rest/server.php'
        req_data: typing.Dict[str, str] = {
            'wstoken': self._token,
            'moodlewsrestformat': 'json',
            'wsfunction': func,
        }
        req_data.update(**kwargs)
        logger.debug(f'Getting {url} with data {req_data}')

        req: requests.Response = requests.get(url, req_data)
        assert req.status_code == 200, req  # FIXME
        data: JsonType = req.json()
        logger.debug(f'Got data: {data}')

        assert 'exception' not in data, data
        assert 'error' not in data, data
        return data

    def configure(self, info: JsonType) -> None:
        self._url: str = info.get('url', 'https://moodle.hsr.ch/')
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
        stats: os.stat_result = path.stat()
        # unfortunately html files have a size of 0
        size: int = 0 if path.suffix == '.html' else stats.st_size
        return self._create_digest(size, int(stats.st_mtime))

    def create_remote_digest(self, path: pathlib.PurePath) -> str:
        moodle_file: _MoodleFile = self._files[path]
        return self._create_digest(moodle_file.size, moodle_file.changed_at)

    def _list_courses(self) -> typing.Iterable[str]:
        courses: typing.List[JsonType] = self._request('core_enrol_get_users_courses',
                                                       userid=str(self._user_id))
        for course in courses:
            self._courses[course['fullname']] = int(course['id'])
        logger.debug(f'Got courses: {self._courses}')
        return list(self._courses)

    def _list_files_in_course(self,
                              course_path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        course = str(course_path)
        if not self._courses:
            self._list_courses()

        course_id: int = self._courses[course]
        lessons: typing.List[JsonType] = self._request('core_course_get_contents',
                                                       courseid=str(course_id))

        for section in lessons:
            section_nr = "{:02d}".format(section['section'])
            section_path: pathlib.PurePath = course_path / f"{section_nr} - {section['name']}"
            for module in section['modules']:
                module_path: pathlib.PurePath = section_path / module['name']
                for elem in module.get('contents', []):
                    filename: str = elem['filename']
                    if 'mimetype' not in elem:
                        # unfortunately html files have a size of 0
                        assert elem['filesize'] == 0, elem
                        if not filename.endswith('.html'):
                            filename += '.html'
                    full_path: pathlib.PurePath = module_path / filename
                    self._files[full_path] = _MoodleFile(elem['fileurl'],
                                                         elem['filesize'],
                                                         elem['timemodified'])
                    logger.debug(f'New file at {full_path}: {self._files[full_path]}')
                    yield full_path

    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        """Get a list of all courses, or files in a course."""
        if path == pathlib.PurePath('/'):
            for course in self._list_courses():
                yield pathlib.PurePath(course)
        else:
            for filename in self._list_files_in_course(path):
                yield filename

    def retrieve_file(self,
                      path: pathlib.PurePath,
                      fileobj: typing.IO[bytes]) -> typing.Optional[int]:
        moodle_file: _MoodleFile = self._files[path]
        logger.debug(f'Getting {moodle_file.url}')

        req: requests.Response = requests.get(moodle_file.url, {'token': self._token})
        assert req.status_code == 200, req  # FIXME
        if 'json' in req.headers['content-type']:
            data: JsonType = req.json()
            assert 'exception' not in data, data
            assert 'error' not in data, data
        for chunk in req:
            fileobj.write(chunk)

        return moodle_file.changed_at

    def connection_schema(self) -> utils.JsonSchemaType:
        return {
            'type': 'object',
            'properties': {
                'url': {'type': 'string'},
            },
            'additionalProperties': False,
        }
