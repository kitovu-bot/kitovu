from kitovu.utils import AbstractReporter


class TestReporter(AbstractReporter):
    def __init__(self, raise_errors=True):
        self.raise_errors = raise_errors
        self.messages = []

    def warn(self, message):
        if self.raise_errors:
            raise Exception(message)
        else:
            self.messages.append(message)