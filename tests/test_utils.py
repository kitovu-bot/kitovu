import pytest

from kitovu import utils


class TestSanitizeFilename():

    @pytest.mark.parametrize('filename,expected', [
        ('test.txt', 'test.txt'),
        ('C: some dir with a colon', 'C_ some dir with a colon'),
        ('With < lt', 'With _ lt'),
        ('With > gt', 'With _ gt'),
        ('* with an asterisk', '_ with an asterisk'),
        ('with a pipe |', 'with a pipe _'),
        (r'my/dir\some_file: with < all > special* chars |', r'my/dir\some_file_ with _ all _ special_ chars _'),
        ('with an underscore _', 'with an underscore _'),
    ])
    def test_with_default_replacement(self, filename, expected):
        assert utils.sanitize_filename(filename) == expected

    @pytest.mark.parametrize('replacement,expected', [
        ('X', r'my/dir\some_fileX with X all X specialX chars X'),
        ('longer', r'my/dir\some_filelonger with longer all longer speciallonger chars longer'),
        (None, r'my/dir\some_file with  all  special chars '),
        ('', r'my/dir\some_file with  all  special chars '),
    ])
    def test_with_a_custom_replacements(self, replacement, expected):
        filename = r'my/dir\some_file: with < all > special* chars |'
        assert utils.sanitize_filename(filename, replacement=replacement) == expected
