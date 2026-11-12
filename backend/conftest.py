import pytest


@pytest.fixture(autouse=True)
def fast_password_hasher(settings):
    """Tests create many users; the real hasher is deliberately slow."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(autouse=True)
def temp_media(settings, tmp_path):
    """Photos written by tests never land in the real media folder."""
    settings.MEDIA_ROOT = tmp_path / "media"
