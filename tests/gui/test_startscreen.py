import pytest

from kitovu.gui import startscreen


@pytest.fixture
def screen(qtbot):
    start = startscreen.StartScreen()
    qtbot.add_widget(start)
    return start


def test_logo_exists(qtbot):
    widget = startscreen.LogoWidget()
    qtbot.add_widget(widget)
    assert not widget._pixmap.isNull()


def test_press_sync(screen, qtbot):
    with qtbot.wait_signal(screen.sync_pressed):
        screen._sync_button.click()


def test_press_conf(screen, qtbot):
    with qtbot.wait_signal(screen.conf_pressed):
        screen._conf_button.click()
