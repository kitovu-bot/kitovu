import pathlib

import pytest
from PyQt5.QtCore import QProcess

from kitovu.gui import syncscreen


class ProcessPatcher:

    def __init__(self, monkeypatch, temppath: pathlib.Path):
        self._monkeypatch = monkeypatch
        self._temppath = temppath

    def patch(self, *code):
        script: pathlib.Path = self._temppath / 'script.py'
        script.write_text('\n'.join(code), encoding='utf-8')
        self._monkeypatch.setattr(syncscreen.SyncScreen, 'PYTHON_ARGS', [str(script)])


@pytest.fixture
def patcher(monkeypatch, temppath):
    return ProcessPatcher(monkeypatch=monkeypatch, temppath=temppath)


@pytest.fixture
def screen(qtbot):
    widget = syncscreen.SyncScreen()
    qtbot.add_widget(widget)
    return widget


def test_success(screen, patcher, qtbot):
    patcher.patch('print("Hello World")')

    with qtbot.wait_signal(screen.finished) as blocker:
        screen.start_sync()

    assert blocker.args[0] == 0
    assert blocker.args[1] == QProcess.NormalExit
    expected_text = '\n'.join([
        'Synchronisation läuft...',
        'Hello World',
        '',
        '',
        'Synchronisation erfolgreich beendet.'
    ])
    assert screen._output.toPlainText() == expected_text


def test_nonzero_exit(screen, patcher, qtbot):
    patcher.patch('import sys',
                  'print("Hello World")',
                  'sys.exit(1)')

    with qtbot.wait_signal(screen.finished) as blocker:
        screen.start_sync()

    assert blocker.args[0] == 1
    assert blocker.args[1] == QProcess.NormalExit
    expected_text = '\n'.join([
        'Synchronisation läuft...',
        'Hello World',
        '',
        '',
        'Fehler: Kitovu-Prozess wurde mit Status 1 beendet.'
    ])
    assert screen._output.toPlainText() == expected_text


@pytest.mark.parametrize('cancel', [True, False])
def test_crash_exit(screen, patcher, qtbot, cancel):
    patcher.patch('import time',
                  'time.sleep(3600)')

    screen.start_sync()

    with qtbot.wait_signal(screen.finished) as blocker:
        if cancel:
            with qtbot.wait_signal(screen.close_requested):
                screen._cancel_button.click()
        else:
            screen._process.kill()

    assert blocker.args[1] == QProcess.CrashExit
    expected_text = '\n'.join([
        'Synchronisation läuft...',
        '',
        'Fehler: Kitovu-Prozess ist abgestürzt.'
    ])
    assert screen._output.toPlainText() == expected_text


def test_stderr_output(screen, patcher, qtbot):
    patcher.patch('import sys',
                  'print("This is stdout", flush=True)',
                  'print("This is stderr", file=sys.stderr, flush=True)')

    with qtbot.wait_signal(screen.finished):
        screen.start_sync()

    expected_text = '\n'.join([
        'Synchronisation läuft...',
        'This is stdout',
        '',
        'This is stderr',
        '',
        'Synchronisation erfolgreich beendet.'
    ])
    assert screen._output.toPlainText() == expected_text


def test_back_button(screen, patcher, qtbot):
    patcher.patch('print("Hello World")')

    with qtbot.wait_signal(screen.finished):
        screen.start_sync()

    with qtbot.wait_signal(screen.close_requested):
        screen._cancel_button.click()


def test_partial_read(screen, patcher, qtbot):
    patcher.patch('print("x", end="")')
    with qtbot.wait_signal(screen.finished):
        screen.start_sync()
