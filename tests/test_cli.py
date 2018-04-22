import pytest

from kitovu.cli import CliReporter


@pytest.fixture
def reporter():
    return CliReporter()


def test_reporter(capsys, reporter):
    reporter.warn("my test")
    reporter.warn("another test")

    captured = capsys.readouterr()
    assert captured.out == "my test\nanother test\n"
    assert captured.err == ""
