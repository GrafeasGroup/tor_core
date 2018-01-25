import json
import logging
import os

from bugsnag.handlers import BugsnagHandler
from praw import Reddit

from tor_core.config import Config
from tor_core.config import Subreddit
from tor_core.heartbeat import configure_heartbeat
from tor_core.helpers import log_header


def configure_tor(config):
    """
    Assembles the tor object based on whether or not we've enabled debug mode
    and returns it. There's really no reason to put together a Subreddit
    object dedicated to our subreddit -- it just makes some future lines
    a little easier to type.

    :param r: the active Reddit object.
    :param config: the global config object.
    :return: the Subreddit object for the chosen subreddit.
    """
    if config.debug_mode:
        tor = config.r.subreddit('tor_testing_ground')
    else:
        # normal operation, our primary subreddit
        tor = config.r.subreddit('transcribersofreddit')

    return tor


def configure_logging(config, log_name='transcribersofreddit.log'):
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s | %(funcName)s | %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S',
    )

    # will intercept anything error level or above
    if config.bugsnag_api_key:
        bs_handler = BugsnagHandler()
        bs_handler.setLevel(logging.ERROR)
        logging.getLogger('').addHandler(bs_handler)
        logging.info('Bugsnag enabled!')
    else:
        logging.info('Not running with Bugsnag!')

    log_header('Starting!')

    return config


def verify_configs(config):
    config_location = os.environ.get('TOR_CONFIG_DIR', '/opt/configs/')
    if not os.path.exists(config_location):
        raise Exception('Cannot load configs! Bad path!')
    config.config_location = config_location
    return config


def populate_subreddit_info(config):
    with open(
            os.path.join(config.config_location, 'bots/subreddits.json')
    ) as subbies:
        subbies = json.load(subbies)
        config.subreddits = [
            Subreddit(
                name,
                reddit_instance=config.r,
                bypass_domain_filter=sub.get('bypass_domain_filter', False),
                upvote_filter=sub.get('upvote_filter', None),
                active=sub.get('active', True),
                no_link_header=sub.get('no_link_header'),
                archive_time=sub.get(
                    'archive_time',
                    subbies['archive_time']['default_delay']
                )
            ) for name, sub in subbies['subreddits'].items()
        ]
    return config


def populate_settings(config):

    # this call returns a full list rather than a generator. PRAW is weird.
    config.mods = config.tor.moderator()

    with open(
            os.path.join(config.config_location + 'bots/settings.json')
    ) as settings:
        settings = json.load(settings)

        config.debug_mode = settings.get('debug_mode', False)
        for giftype in settings['gifs'].keys():
            # this will automatically load in every set of gifs under the
            # heading name. For example, config.gifs.no
            config.gifs.set(giftype, settings['gifs'][giftype])

        config.no_gifs = settings['gifs']['no']
        config.thumbs_up_gifs = settings['gifs']['thumbs_up']

    with open(
            os.path.join(config.config_location + 'templates/audio/base.md')
    ) as audio:
        config.media['audio'].base_format = ''.join(audio.readlines())
        config.media['audio'].domains = settings['filters']['domains']['audio']

    with open(
            os.path.join(config.config_location + 'templates/video/base.md')
    ) as video:
        config.media['video'].base_format = ''.join(video.readlines())
        config.media['video'].domains = settings['filters']['domains']['video']

    with open(
            os.path.join(config.config_location + 'templates/image/base.md')
    ) as images:
        config.media['image'].base_format = ''.join(images.readlines())
        config.media['image'].domains = settings['filters']['domains']['images']

    with open(
            os.path.join(config.config_location + 'templates/other/base.md')
    ) as other:
        config.media['other'].base_format = ''.join(other.readlines())

    with open(
            os.path.join(config.config_location + 'bots/footer.md')
    ) as footer:
        config.footer = ''.join(footer.readlines()).strip()
    return config


def initialize(temp_config):
    temp_config = verify_configs(temp_config)

    temp_config = populate_subreddit_info(temp_config)
    logging.info('Subreddit information loaded.')

    temp_config = populate_settings(temp_config)
    logging.info('Settings loaded.')

    return temp_config


def build_bot(
    name,
    version,
    full_name=None,
    log_name='transcribersofreddit.log',
    require_redis=True,
    heartbeat_logging=False
):
    """
    Shortcut for setting up a bot instance. Runs all configuration and returns
    a valid config object.

    :param name: string; The name of the bot to be started; this name must
        match the settings in praw.ini
    :param version: string; the version number for the current bot being run
    :param full_name: string; the descriptive name of the current bot being
        run; this is used for the heartbeat and status
    :param log_name: string; the name to be used for the log file on disk. No
        spaces.
    :param require_redis: bool; triggers the creation of the Redis instance.
        Any bot that does not require use of Redis can set this to False and
        not have it crash on start because Redis isn't running.
    :param heartbeat_logging: bool; enables extremely verbose logging from
        CherryPy on heartbeat activity.
    :return: object; the freshly built config object.
    """
    config = Config()
    config.r = Reddit(name)
    # this is used to power messages, so please add a full name if you can
    config.name = full_name if full_name else name
    config.bot_version = version
    config.heartbeat_logging = heartbeat_logging
    config = configure_logging(config, log_name=log_name)

    config = initialize(config)

    if require_redis:
        # we want this to run after the config object is created
        # and for this version, heartbeat requires db access
        configure_heartbeat(config)

    logging.info('Bot built and initialized!')
    return config
