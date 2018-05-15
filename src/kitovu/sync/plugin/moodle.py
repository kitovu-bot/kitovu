"""A plugin which talks to Moodle using its Web Services."""

import os
import typing
import pathlib
import logging

import attr
import requests

from kitovu import utils
from kitovu.sync import syncplugin


logger: logging.Logger = logging.getLogger(__name__)


@attr.s
class _MoodleFile:

    url: str = attr.ib()
    size: int = attr.ib()
    changed_at: int = attr.ib()


class MoodlePlugin(syncplugin.AbstractSyncPlugin):

    NAME = 'moodle'

    def __init__(self) -> None:
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
        try:
            req.raise_for_status()
        except requests.exceptions.HTTPError as ex:
            raise utils.PluginOperationError(f"HTTP error: {ex}.")

        data: utils.JsonType = req.json()
        logger.debug(f'Got data: {data}')
        self._check_json_answer(data)
        return data

    def _check_json_answer(self, data: utils.JsonType) -> None:
        if not isinstance(data, dict):
            # For some requests, Moodle responds with an JSON array (list) and
            # not a JSON object (dict). However, in case of an error, we always
            # get a dict - so we bail out early and assume a correct answer if
            # we get something else.
            return

        errorcode: str = data.get("errorcode", None)
        if errorcode == "invalidtoken":
            raise utils.AuthenticationError(data['message'])
        elif errorcode == "invalidrecord":  # e.g. invalid ws_function, invalid course ID
            # given error message is hard to understand,
            # writing a better to understand one instead
            raise utils.PluginOperationError(
                "You requested something from Moodle which it couldn't get.")
        elif "exception" in data:  # base case for errors
            raise utils.PluginOperationError(data["message"])

    def configure(self, info: utils.JsonType) -> None:
        self._url: str = info.get('url', 'https://moodle.hsr.ch/')
        if not self._url.endswith('/'):
            self._url += '/'

        prompt = f"Enter token from {self._url}user/preferences.php -> Sicherheitsschlüssel"
        self._token = utils.get_password('moodle', self._url, prompt)

    def connect(self) -> None:
        """Get the user ID associated with the token entered by the user."""
        site_info: utils.JsonType = self._request('core_webservice_get_site_info')
        self._user_id: int = site_info['userid']

    def disconnect(self) -> None:
        pass

    def _create_digest(self, size: int, changed_at: int) -> str:
        return f'{size}-{changed_at}'

    def create_local_digest(self, path: pathlib.Path) -> str:
        stats: os.stat_result = path.stat()
        # Unfortunately, Moodle returns a size of 0 for HTML files in its API.
        size: int = 0 if path.suffix == '.html' else stats.st_size
        mtime = int(stats.st_mtime)
        return self._create_digest(size, mtime)

    def create_remote_digest(self, path: pathlib.PurePath) -> str:
        moodle_file: _MoodleFile = self._files[path]
        return self._create_digest(moodle_file.size, moodle_file.changed_at)

    def _list_courses(self) -> typing.Iterable[str]:
        courses: typing.List[utils.JsonType] = self._request('core_enrol_get_users_courses',
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

        if course not in self._courses:
            raise utils.PluginOperationError(f"The remote-dir '{course}' was not found.")
        course_id: int = self._courses[course]

        lessons: typing.List[utils.JsonType] = self._request('core_course_get_contents',
                                                             courseid=str(course_id))

        for section in lessons:
            section_nr = "{:02d}".format(section['section'])
            section_path: pathlib.PurePath = course_path / f"{section_nr} - {section['name']}"
            for module in section['modules']:
                module_path: pathlib.PurePath = section_path / module['name']
                for elem in module.get('contents', []):
                    filename: str = elem['filename']
                    if 'mimetype' not in elem:
                        # Unfortunately, Moodle returns a size of 0 for HTML files in its API.
                        # Also, HTML files are the only entries without a mimetype set.
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
        assert self._files, "list_path was never called, no files available."
        moodle_file: _MoodleFile = self._files[path]
        logger.debug(f'Getting {moodle_file.url}')

        req: requests.Response = requests.get(moodle_file.url, {'token': self._token})
        try:
            req.raise_for_status()
        except requests.exceptions.HTTPError as ex:
            raise utils.PluginOperationError(f"HTTP error: {ex}.")

        # Errors from Moodle are delivered as json.
        if 'json' in req.headers['content-type']:
            data: utils.JsonType = req.json()
            self._check_json_answer(data)

        for chunk in req:
            fileobj.write(chunk)

        return moodle_file.changed_at

    def connection_schema(self) -> utils.JsonType:
        return {
            'type': 'object',
            'properties': {
                'url': {'type': 'string'},
            },
            'additionalProperties': False,
        }
