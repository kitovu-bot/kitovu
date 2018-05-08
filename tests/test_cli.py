import pytest
import pathlib

from click.testing import CliRunner

from kitovu import cli


@pytest.fixture
def reporter():
    return cli.CliReporter()


@pytest.fixture
def runner():
    return CliRunner()


def test_reporter(capsys, reporter):
    reporter.warn("my test")
    reporter.warn("another test")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "my test\nanother test\n"


def test_docs(runner, mocker):
    mock = mocker.patch('webbrowser.open_new_tab', autospec=True)

    runner.invoke(cli.docs)

    mock.assert_called_once_with('https://kitovu.readthedocs.io/en/latest')


class TestEdit:

    @pytest.fixture(autouse=True)
    def clear_env(self, monkeypatch):
        monkeypatch.delenv('EDITOR', raising=False)

    class TestMissing:

        @pytest.fixture(autouse=True)
        def patch(self, monkeypatch):
            self.checked_editors = []
            monkeypatch.setattr('distutils.spawn.find_executable', self._find_executable_patch)

        def test_defaults(self, runner):
            result = runner.invoke(cli.edit)

            assert result.exit_code == 1

            assert self.checked_editors == ['vim', 'emacs', 'nano', 'editor', 'notepad']
            assert result.output == 'Could not find a valid editor\n'

        def test_from_args(self, runner):
            result = runner.invoke(cli.edit, ['--editor', 'myeditor'])

            assert result.exit_code == 1

            assert self.checked_editors == ['myeditor']
            assert result.output == 'Could not find the editor myeditor\n'

        def test_from_env(self, runner, monkeypatch):
            monkeypatch.setenv('EDITOR', 'editor_from_env')

            result = runner.invoke(cli.edit)

            assert result.exit_code == 1

            assert self.checked_editors == ['editor_from_env']
            assert result.output == 'Could not find the editor editor_from_env\n'

        def _find_executable_patch(self, editor):
            self.checked_editors.append(editor)
            return None

    class TestAvailable:

        @pytest.fixture(autouse=True)
        def patch(self, monkeypatch):
            self.checked_editors = []
            monkeypatch.setattr('distutils.spawn.find_executable', self._find_executable_patch)

            self.subprocess_calls = []
            monkeypatch.setattr('subprocess.call', lambda args: self.subprocess_calls.append(args))

        def test_with_an_available_editor(self, runner, monkeypatch):
            result = runner.invoke(cli.edit, ['--config', 'test.yml'])

            assert result.exception is None
            assert result.exit_code == 0

            assert self.checked_editors == ['vim']
            assert result.output == ''
            assert self.subprocess_calls == [['/some/example/path/vim', pathlib.Path('test.yml')]]

        def test_with_an_available_editor_from_the_args(self, runner, monkeypatch):
            result = runner.invoke(cli.edit, ['--editor', 'myeditor', '--config', 'test.yml'])

            assert result.exception is None
            assert result.exit_code == 0

            assert self.checked_editors == ['myeditor']
            assert result.output == ''
            assert self.subprocess_calls == [['/some/example/path/myeditor', pathlib.Path('test.yml')]]

        def test_with_an_available_editor_from_the_env(self, runner, monkeypatch):
            monkeypatch.setenv('EDITOR', 'editor_from_env')

            result = runner.invoke(cli.edit, ['--config', 'test.yml'])

            assert result.exception is None
            assert result.exit_code == 0

            assert self.checked_editors == ['editor_from_env']
            assert result.output == ''
            assert self.subprocess_calls == [['/some/example/path/editor_from_env', pathlib.Path('test.yml')]]

        def _find_executable_patch(self, editor):
            self.checked_editors.append(editor)
            return f'/some/example/path/{editor}'
