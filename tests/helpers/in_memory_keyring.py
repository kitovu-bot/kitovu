import keyring.backend
import pytest


class InMemoryKeyring(keyring.backend.KeyringBackend):
    priority = 1

    _passwords = {}

    def set_password(self, servicename, username, password):
        self._passwords[(servicename, username)] = password

    def get_password(self, servicename, username):
        return self._passwords.get((servicename, username))

    def delete_password(self, servicename, username):
        self._passwords.pop((servicename, username))

    def clear(self):
        self._passwords.clear()
