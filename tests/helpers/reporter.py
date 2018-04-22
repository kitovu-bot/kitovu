from kitovu.utils import AbstractReporter


class TestReporter(AbstractReporter):
    def __init__(self, raise_errors=False):
        self.raise_errors = raise_errors

    def warning(self, message):
        if self.raise_errors:
            raise Exception(message)
