import pytest

from kitovu import utils


class TestSanitizeFilename():

    @pytest.mark.parametrize('filename,expected', [
        ('test.txt', 'test.txt'),
        ('some test / another', 'some test _ another'),
        ('my dir\\with backslash', 'my dir_with backslash'),
        ('C: some dir with a colon', 'C_ some dir with a colon'),
        ('With < lt', 'With _ lt'),
        ('With > gt', 'With _ gt'),
        ('* with an asterisk', '_ with an asterisk'),
        ('with a pipe |', 'with a pipe _'),
        ('my/dir\\some_file: with < all > special* chars |', 'my_dir_some_file_ with _ all _ special_ chars _'),
        ('with an underscore _', 'with an underscore _'),
    ])
    def test_with_default_replacement(self, filename, expected):
        assert utils.sanitize_filename(filename) == expected

    @pytest.mark.parametrize('replacement,expected', [
        ('X', 'myXdirXsome_fileX with X all X specialX chars X'),
        ('some_longer', 'mysome_longerdirsome_longersome_filesome_longer with some_longer all some_longer specialsome_longer chars some_longer'),
        (None, 'mydirsome_file with  all  special chars '),
        ('', 'mydirsome_file with  all  special chars '),
    ])
    def test_with_a_custom_replacements(self, replacement, expected):
        filename = 'my/dir\\some_file: with < all > special* chars |'
        assert utils.sanitize_filename(filename, replacement=replacement) == expected
