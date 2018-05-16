import pytest

from click.testing import CliRunner

from kitovu import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_docs(runner, mocker):
    mock = mocker.patch('webbrowser.open_new_tab', autospec=True)

    runner.invoke(cli.docs)

    mock.assert_called_once_with('https://kitovu.readthedocs.io/en/latest')


def test_fileinfo(runner):
    result = runner.invoke(cli.fileinfo)
    lines = result.output.splitlines()
    assert lines[0].startswith("The configuration file is located at:")
    assert lines[1].startswith("The file cache is located at:")


def test_sync_invalid(runner, temppath):
    config = temppath / 'does-not-exist'
    result = runner.invoke(cli.sync, ['--config', str(config)])
    assert result.output.strip() == f'Error: Could not find the file {config}'
    assert result.exit_code == 1


class TestValidate:

    def test_valid(self, runner, temppath):
        config = temppath / 'kitovu.yml'
        config.write_text(f"""
        root-dir: {temppath}
        connections: []
        subjects: []
        """, encoding='utf-8')

        result = runner.invoke(cli.validate, ['--config', str(config)])
        assert result.output == ''
        assert result.exit_code == 0

    def test_invalid(self, runner, temppath):
        config = temppath / 'kitovu.yml'
        config.touch()

        result = runner.invoke(cli.validate, ['--config', str(config)])
        assert result.output.startswith("Error: None is not of type 'object'")
        assert result.exit_code == 1


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
            assert result.output == 'Error: Could not find a valid editor\n'

        def test_from_args(self, runner):
            result = runner.invoke(cli.edit, ['--editor', 'myeditor'])

            assert result.exit_code == 1

            assert self.checked_editors == ['myeditor']
            assert result.output == 'Error: Could not find the editor myeditor\n'

        def test_from_env(self, runner, monkeypatch):
            monkeypatch.setenv('EDITOR', 'editor_from_env')

            result = runner.invoke(cli.edit)

            assert result.exit_code == 1

            assert self.checked_editors == ['editor_from_env']
            assert result.output == 'Error: Could not find the editor editor_from_env\n'

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

        def test_with_a_missing_config(self, runner, monkeypatch, temppath):
            config = temppath / 'test.yml'
            result = runner.invoke(cli.edit, ['--config', config])

            assert result.exit_code == 1

            assert result.output == f'Error: Could not find the configuration file {config}\n'

        def test_with_an_available_editor(self, runner, monkeypatch, temppath):
            config = temppath / 'test.yml'
            config.touch()
            result = runner.invoke(cli.edit, ['--config', config])

            assert result.exception is None
            assert result.exit_code == 0

            assert self.checked_editors == ['vim']
            assert result.output == ''
            assert self.subprocess_calls == [['/some/example/path/vim', config]]

        def test_with_an_available_editor_from_the_args(self, runner, monkeypatch, temppath):
            config = temppath / 'test.yml'
            config.touch()
            result = runner.invoke(cli.edit, ['--editor', 'myeditor', '--config', config])

            assert result.exception is None
            assert result.exit_code == 0

            assert self.checked_editors == ['myeditor']
            assert result.output == ''
            assert self.subprocess_calls == [['/some/example/path/myeditor', config]]

        def test_with_an_available_editor_from_the_env(self, runner, monkeypatch, temppath):
            monkeypatch.setenv('EDITOR', 'editor_from_env')

            config = temppath / 'test.yml'
            config.touch()
            result = runner.invoke(cli.edit, ['--config', config])

            assert result.exception is None
            assert result.exit_code == 0

            assert self.checked_editors == ['editor_from_env']
            assert result.output == ''
            assert self.subprocess_calls == [['/some/example/path/editor_from_env', config]]

        def _find_executable_patch(self, editor):
            self.checked_editors.append(editor)
            return f'/some/example/path/{editor}'
