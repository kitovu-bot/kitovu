import keyring.backend


class InMemoryKeyring(keyring.backend.KeyringBackend):

    priority = 1

    def __init__(self):
        super().__init__()
        self._passwords = {}

    def set_password(self, servicename, username, password):
        self._passwords[(servicename, username)] = password

    def get_password(self, servicename, username):
        try:
            return self._passwords[(servicename, username)]
        except KeyError:
            return None

    def delete_password(self, servicename, username):
        # Not used yet, but might be useful in the future
        del self._passwords[(servicename, username)]  # pragma: no cover

    def clear(self):
        self._passwords.clear()
