import pytest
import keyring

from helpers.in_memory_keyring import InMemoryKeyring


@pytest.fixture(autouse=True)
def init_keyring():
    ring = InMemoryKeyring()
    keyring.set_keyring(ring)
    yield
    ring.clear()
