import pytest

from kitovu.gui import mainwindow


@pytest.fixture
def window(qtbot):
    widget = mainwindow.MainWindow()
    qtbot.add_widget(widget)
    return widget


def test_main_window_status_bar(window):
    window.centralWidget().status_message.emit("Hello World")
    assert window.statusBar().currentMessage() == "Hello World"


def test_switching_to_conf_screen(window, qtbot):
    window.show()
    qtbot.wait_for_window_shown(window)

    central: mainwindow.CentralWidget = window.centralWidget()
    assert central._start_screen.isVisible()

    central._start_screen._conf_button.click()
    assert not central._start_screen.isVisible()
    assert central._conf_screen.isVisible()

    central._conf_screen._cancel_button.click()
    assert not central._conf_screen.isVisible()
    assert central._start_screen.isVisible()


def test_switching_to_sync_screen(window, monkeypatch, qtbot):
    window.show()
    qtbot.wait_for_window_shown(window)

    central: mainwindow.CentralWidget = window.centralWidget()
    assert central._start_screen.isVisible()

    central._start_screen._sync_button.click()
    assert not central._start_screen.isVisible()
    assert central._sync_screen.isVisible()

    central._conf_screen._cancel_button.click()
    assert not central._conf_screen.isVisible()
    assert central._start_screen.isVisible()
