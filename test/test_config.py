import pytest

import redis.exceptions

from tor_core.config import Config as SITE_CONFIG
from tor_core.config import AudioConfig
from tor_core.config import VideoConfig
from tor_core.config import ImageConfig
from tor_core.config import OtherContentConfig


@pytest.mark.skip
def test_read_secrets_from_filesystem():
    """Secret data has been read from the filesystem
    """
    assert SITE_CONFIG.bugsnag_api_key is not None
    assert SITE_CONFIG.slack_api_key is not None


def test_config_structure():
    """
    Config singleton is structured as expected
    """
    assert isinstance(SITE_CONFIG.media, dict)
    assert len(SITE_CONFIG.media) == 4

    assert isinstance(SITE_CONFIG.media['audio'].domains, list)
    assert isinstance(SITE_CONFIG.media['audio'], AudioConfig)
    assert isinstance(SITE_CONFIG.media['audio'].base_format, type(None))

    assert isinstance(SITE_CONFIG.media['video'].domains, list)
    assert isinstance(SITE_CONFIG.media['video'], VideoConfig)
    assert isinstance(SITE_CONFIG.media['video'].base_format, type(None))

    assert isinstance(SITE_CONFIG.media['image'].domains, list)
    assert isinstance(SITE_CONFIG.media['image'], ImageConfig)
    assert isinstance(SITE_CONFIG.media['image'].base_format, type(None))

    assert isinstance(SITE_CONFIG.media['other'].domains, list)
    assert isinstance(SITE_CONFIG.media['other'], OtherContentConfig)
    assert isinstance(SITE_CONFIG.media['other'].base_format, type(None))

    assert isinstance(SITE_CONFIG.footer, str)

    assert isinstance(SITE_CONFIG.subreddits, list)

    assert isinstance(SITE_CONFIG.mods, list)

    assert isinstance(SITE_CONFIG.perform_footer_check, bool)
    assert isinstance(SITE_CONFIG.debug_mode, bool)

    assert isinstance(SITE_CONFIG.no_gifs, list)

    assert isinstance(SITE_CONFIG.OCR, bool)

    assert isinstance(SITE_CONFIG.bugsnag_api_key, str) or \
        SITE_CONFIG.bugsnag_api_key is None

    assert isinstance(SITE_CONFIG.slack_api_key, str) or \
        SITE_CONFIG.slack_api_key is None


def test_redis_config_property():
    try:
        assert SITE_CONFIG.redis, 'Does not observe lazy loader'
    except redis.exceptions.ConnectionError:
        pass

    with pytest.raises(AttributeError):
        SITE_CONFIG.redis.ping()
