import pytest

import helpers.reporter


def test_reporter_with_defaults():
    reporter = helpers.reporter.TestReporter()
    reporter.warn("test 1")
    reporter.warn("test 2")

    assert reporter.messages == [
        "test 1",
        "test 2",
    ]


def test_reporter_without_raising():
    reporter = helpers.reporter.TestReporter(raise_errors=False)
    reporter.warn("my test")
    reporter.warn("another test")

    assert reporter.messages == [
        "my test",
        "another test",
    ]


def test_reporter_with_raising():
    reporter = helpers.reporter.TestReporter(raise_errors=True)
    with pytest.raises(Exception) as excinfo:
        reporter.warn("my test")
    assert str(excinfo.value) == "my test"

    with pytest.raises(Exception) as excinfo:
        reporter.warn("another test")
    assert str(excinfo.value) == "another test"
