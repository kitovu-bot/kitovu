import pytest
import keyring

from helpers.in_memory_keyring import InMemoryKeyring

keyring.set_keyring(InMemoryKeyring())


@pytest.fixture(autouse=True)
def clear_keyring(request):
    keyring.get_keyring().clear()
