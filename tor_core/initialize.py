import logging
import os
import random
import sys
import json

import redis
from bugsnag.handlers import BugsnagHandler
from praw import Reddit

from tor_core.config import config
from tor_core.heartbeat import configure_heartbeat
from tor_core.helpers import clean_list
from tor_core.helpers import get_wiki_page
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
        format='[%(asctime)s] - [%(levelname)s] - [%(funcName)s] - %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        filename=log_name
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s] - [%(funcName)s] - %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)

    # add the handlers to the root logger
    logging.getLogger('').addHandler(console)
    # will intercept anything error level or above
    if config.bugsnag_api_key:
        bs_handler = BugsnagHandler()
        bs_handler.setLevel(logging.ERROR)
        logging.getLogger('').addHandler(bs_handler)
        logging.info('Bugsnag enabled!')
    else:
        logging.info('Not running with Bugsnag!')

    log_header('Starting!')


def populate_subreddit_lists(config):
    """
    Gets the list of subreddits to monitor and loads it into memory.

    :return: None.
    """


    for line in get_wiki_page(
        'subreddits/upvote-filtered', config
    ).splitlines():
        if ',' in line:
            sub, threshold = line.split(',')
            config.upvote_filter_subs[sub] = int(threshold)

    logging.debug(
        'Retrieved subreddits subject to the upvote filter: {}'.format(
            config.upvote_filter_subs
        )
    )

    config.subreddits_domain_filter_bypass = get_wiki_page(
        'subreddits/domain-filter-bypass', config
    ).split('\r\n')
    config.subreddits_domain_filter_bypass = clean_list(
        config.subreddits_domain_filter_bypass
    )
    logging.debug(
        'Retrieved subreddits that bypass the domain filter: {}'.format(
            config.subreddits_domain_filter_bypass
        )
    )



def verify_configs(config):
    config_location = os.environ.get('TOR_CONFIG_DIR', '/opt/configs')
    if not os.path.exists(config_location):
        raise Exception('Cannot load configs! Bad path!')
    config.config_location = config_location

def populate_subreddit_info(config):
    with open(config.config_location + '/bots/subreddits.json') as subbies:
        subbies = json.load(subbies)['subreddits']
        config.subreddits_to_check = [
            sub for sub in subbies.keys() if not \
                subbies[sub].get('active') is False
        ]

        config.upvote_filter_subs = dict()
        for sub in subbies.keys():
            if subbies[sub].get('upvote_filter') is not None:
                config.upvote_filter_subs[sub] = int(
                    subbies[sub].get('upvote_filter')
                )

        config.archive_time_default = subbies['archive_time']['default_delay']

        config.archive_time_subreddits = dict()
        for sub in subbies.keys():
            config.archive_time_subreddits[sub] = (
                subbies[sub].get('archive_time') if
                subbies[sub].get('archive_time') is not None else
                config.archive_time_default
            )

        config.no_link_header_subs = [
            sub for sub in subbies.keys() if
            subbies[sub].get('no_link_header') is True
        ]


def populate_settings(config):

    # this call returns a full list rather than a generator. Praw is weird.
    config.mods = config.tor.moderator()

    with open(config.config_location + '/bots/settings.json') as settings:
        settings = json.load(settings)

        config.no_gifs = settings['gifs']['no']
        config.thumbs_up_gifs = settings['gifs']['thumbs_up']

    with open(config.config_location + '/templates/audio/base.md') as audio:
        config.media['audio'].base_format = ''.join(audio.readlines())
        config.media['audio'].domains = settings['filters']['domains']['audio']

    with open(config.config_location + '/templates/video/base.md') as video:
        config.media['video'].base_format = ''.join(video.readlines())
        config.media['video'].domains = settings['filters']['domains']['video']

    with open(config.config_location + '/templates/image/base.md') as images:
        config.media['image'].base_format = ''.join(images.readlines())
        config.media['image'].domains = settings['filters']['domains']['images']

    with open(config.config_location + '/templates/other/base.md') as other:
        config.media['other'].base_format = ''.join(other.readlines())


def initialize(config):
    verify_configs(config)

    populate_subreddit_info(config)
    logging.debug('Subreddit information loaded.')

    populate_settings(config)
    logging.debug('Settings loaded.')


def get_heartbeat_port(config):
    """
    Attempts to pull an existing port number from the filesystem, and if it
    doesn't find one then it generates the port number and saves it to a key
    file.

    :param config: the global config object
    :return: int; the port number to use.
    """
    try:
        # have we already reserved a port for this process?
        with open('heartbeat.port', 'r') as port_file:
            port = int(port_file.readline().strip())
        logging.debug('Found existing port saved on disk')
        return port
    except OSError:
        pass

    while True:
        port = random.randrange(40000, 40200)  # is 200 ports too much?
        if config.redis.sismember('active_heartbeat_ports', port) == 0:
            config.redis.sadd('active_heartbeat_ports', port)

            # create that file we looked for earlier
            with open('heartbeat.port', 'w') as port_file:
                port_file.write(str(port))
            logging.debug('generated port {} and saved to disk'.format(port))

            return port


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
    :return: None
    """

    config.r = Reddit(name)
    # this is used to power messages, so please add a full name if you can
    config.name = full_name if full_name else name
    config.bot_version = version
    config.heartbeat_logging = heartbeat_logging
    configure_logging(config, log_name=log_name)

    if not require_redis:
        # I'm sorry
        type(config).redis = property(lambda x: (_ for _ in ()).throw(NotImplementedError('Redis was disabled during building!')))

    initialize(config)

    if require_redis:
        # we want this to run after the config object is created
        # and for this version, heartbeat requires db access
        configure_heartbeat(config)

    logging.info('Bot built and initialized!')
