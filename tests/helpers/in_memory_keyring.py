import keyring.backend


class InMemoryKeyring(keyring.backend.KeyringBackend):

    priority = 1
    _passwords = {}

    def set_password(self, servicename, username, password):
        self._passwords[(servicename, username)] = password

    def get_password(self, servicename, username):
        return self._passwords[(servicename, username)]

    def delete_password(self, servicename, username):
        del self._passwords[(servicename, username)]

    def clear(self):
        self._passwords.clear()
