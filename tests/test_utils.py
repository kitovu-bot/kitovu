import keyring
import pytest
import pathlib

from kitovu import utils


class TestSanitizeFilename:

    @pytest.mark.parametrize('filename,expected', [
        ('test.txt', 'test.txt'),
        ('C: some dir with a colon', 'C_ some dir with a colon'),
        ('With < lt', 'With _ lt'),
        ('With > gt', 'With _ gt'),
        ('* with an asterisk', '_ with an asterisk'),
        ('with a pipe |', 'with a pipe _'),
        (r'my/dir\some_file: with < all > special* chars |', r'my/dir\some_file_ with _ all _ special_ chars _'),
        ('with an underscore _', 'with an underscore _'),
    ])
    def test_santize(self, filename, expected):
        assert utils.sanitize_filename(pathlib.PurePath(filename)) == pathlib.PurePath(expected)


def test_password_prompt(mocker):
    mock = mocker.patch('getpass.getpass', autospec=True)
    mock.return_value = 'hunter2'
    utils.get_password('dummyplugin', 'identifier', 'prompt')
    mock.assert_called_once_with('Enter password for dummyplugin (prompt): ')
    assert keyring.get_password('kitovu-dummyplugin', 'identifier') == 'hunter2'
