import pathlib

import pytest
import pytest-responses
import responses

from kitovu.sync import syncing
from kitovu import utils
from kitovu.sync.plugin import moodle


class TestConnect:

    def test_connect_with_default_options(self):
        pass

    def test_connect_with_custom_options(self):
        pass

    def test_connect_with_hsr_config(self):
        pass


class TestValidations:

    def test_config_with_all_available_fields(self):
        pass

    def test_config_with_minimum_required_fields(self):
        pass

    def test_config_with_unexpected_fields(self):
        pass


class TestWithConnectedPlugin:

    def test_create_remote_digest(self):
        pass

    def test_disconnect(self):
        pass

    def test_list_path(self):
        pass
