import kitovu.utils
import pytest

from tests.helpers import dummyplugin


dummy = dummyplugin.DummyPlugin()


def test_connection_active() -> None:
    dummy.connect()
    assert dummy.connection_state == True


def test_conection_inactive() -> None:
    dummy.disconnect()
    assert dummy.connection_state == False


