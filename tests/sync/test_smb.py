import pytest

from kitovu.sync import smb


@pytest.mark.parametrize('url, expected', [
    # @hsr.ch shorthand
    ('smb://testuser@hsr.ch', smb._LoginInfo(
        username='testuser', hostname='svm-c213.hsr.ch', share='skripte',
        domain='HSR', port=445)),
    # Other SMB server
    ('smb://user@example.com/share', smb._LoginInfo(
        username='user', hostname='example.com', share='share',
        domain=None, port=None)),
    # Other server with domain
    ('smb://user;domain@example.com/share', smb._LoginInfo(
        username='user', hostname='example.com', share='share',
        domain='domain', port=None)),
])
def test_parse_url(url: str, expected: smb._LoginInfo):
    assert smb._parse_url(url) == expected
