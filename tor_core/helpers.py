import logging
import re
import sys
import time

import prawcore
import requests

from tor_core import __version__
from tor_core.config import config
from tor_core.heartbeat import stop_heartbeat_server
from tor_core.strings import bot_footer
from addict import Dict

subreddit_regex = re.compile(
    'reddit.com\/r\/([a-z0-9\-\_\+]+)',
    flags=re.IGNORECASE
)

default_exceptions = (
    prawcore.exceptions.RequestException,
    prawcore.exceptions.ServerError,
    prawcore.exceptions.Forbidden
)

flair = Dict()
flair.unclaimed = 'Unclaimed'
flair.summoned_unclaimed = 'Summoned - Unclaimed'
flair.completed = 'Completed!'
flair.in_progress = 'In Progress'
flair.meta = 'Meta'
flair.disregard = 'Disregard'

css_flair = Dict()
css_flair.unclaimed = 'unclaimed'
css_flair.completed = 'transcriptioncomplete'
css_flair.in_progress = 'inprogress'
css_flair.meta = 'meta'
css_flair.disregard = 'disregard'


def _(message):
    """
    Message formatter. Returns the message and the disclaimer for the
    footer.

    :param message: string. The message to be displayed.
    :return: string. The original message plus the footer.
    """
    return bot_footer.format(message, version=__version__)


def log_header(message):
    logging.info('*' * 50)
    logging.info(message)
    logging.info('*' * 50)


def clean_list(items):
    """
    Takes a list and removes entries that are only newlines.

    :param items: List.
    :return: List, sans newlines
    """
    cleaned = []
    for item in items:
        if item.strip() != '':
            cleaned.append(item)

    return cleaned


def send_to_slack(message, config):
    """
    Sends a message to the ToR #general slack channel.

    :param message: String; the message that is to be encoded.
    :param config: the global config dict.
    :return: None.
    """
    # if we have the api url loaded, then fire off the message.
    # Otherwise, don't worry about it and just return.
    if config.slack_api_url:
        payload = {
            'username': 'Kierra',
            'icon_emoji': ':snoo:',
            'text': message
        }
        requests.post(config.slack_api_url, json=payload)

    return


def explode_gracefully(error, config):
    """
    A last-ditch effort to try to raise a few more flags as it goes down.
    Only call in times of dire need.

    :param bot_name: string; the name of the bot calling the method.
    :param error: an exception object.
    :param tor: the r/ToR helper object
    :return: Nothing. Everything dies here.
    """
    logging.error(error)

    config.tor.message(
        '{} BROKE - {}'.format(config.name, error.__class__.__name__.upper()),
        'Please check Bugsnag for the complete error.'
    )
    sys.exit(1)


def subreddit_from_url(url):
    """
    Returns the subreddit a post was made in, based on its reddit URL
    """
    m = subreddit_regex.search(url)
    if m is not None:
        return m.group(1)
    return None


def clean_id(post_id):
    """
    Fixes the Reddit ID so that it can be used to get a new object.

    By default, the Reddit ID is prefixed with something like `t1_` or
    `t3_`, but this doesn't always work for getting a new object. This
    method removes those prefixes and returns the rest.

    :param post_id: String. Post fullname (ID)
    :return: String. Post fullname minus the first three characters.
    """
    return post_id[post_id.index('_') + 1:]


def get_parent_post_id(post, r):
    """
    Takes any given comment object and returns the object of the
    original post, no matter how far up the chain it is. This is
    a very time-intensive function because of how Reddit handles
    rate limiting and the fact that you can't just request the
    top parent -- you have to just loop your way to the top.

    :param post: comment object
    :param r: the instantiated reddit object
    :return: submission object of the top post.
    """
    while True:
        if not post.is_root:
            post = r.comment(id=clean_id(post.parent_id))
        else:
            return r.submission(id=clean_id(post.parent_id))


def get_wiki_page(pagename, config, return_on_fail=None):
    """
    Return the contents of a given wiki page.

    :param pagename: String. The name of the page to be requested.
    :param tor: Active ToR instance.
    :param return_on_fail: Any value to return when nothing is found
        at the requested page. This allows us to specify returns for
        easier work in debug mode.
    :return: String or None. The content of the requested page if
        present else None.
    """
    logging.debug('Retrieving wiki page {}'.format(pagename))
    try:
        result = config.tor.wiki[pagename].content_md
        return result if result != '' else return_on_fail
    except prawcore.exceptions.NotFound:
        return return_on_fail


def update_wiki_page(pagename, content, config):
    """
    Sends new content to the requested wiki page.

    :param pagename: String. The name of the page to be edited.
    :param content: String. New content for the wiki page.
    :param tor: Active ToR instance.
    :return: None.
    """

    logging.debug('Updating wiki page {}'.format(pagename))

    try:
        return config.tor.wiki[pagename].edit(content)
    except prawcore.exceptions.NotFound as e:
        logging.error(
            '{} - Requested wiki page {} not found. '
            'Cannot update.'.format(e, pagename)
        )


def deactivate_heartbeat_port(port):
    """
    This isn't used as part of the normal functions; when a port is created,
    it gets used again and again. The point of this function is to deregister
    the port that the status page checks, but would probably only be used by
    the command line.

    :param port: int, the port number
    :return: None
    """
    config.redis.srem('active_heartbeat_ports', port)
    logging.info('Removed port from set of heartbeats.')


def stop_heartbeat(config):
    """
    Any logic that goes along with stopping the cherrypy heartbeat server goes
    here. This is called on exit of `run_until_dead()`, either through keyboard
    or crash. The heartbeat server will terminate if the process dies anyway,
    but this allows for a clean shutdown.

    :param config: the global config object
    :return: None
    """
    stop_heartbeat_server()
    logging.info('Stopped heartbeat!')


def run_until_dead(func, exceptions=default_exceptions):
    """
    The official method that replaces all that ugly boilerplate required to
    start up a bot under the TranscribersOfReddit umbrella. This method handles
    communication issues with Reddit, timeouts, and handles CTRL+C and
    unexpected crashes.

    :param func: The function that you want to run; this will automatically be
        passed the config object. Historically, this is the only thing needed
        to start a bot.
    :param exceptions: A tuple of exception classes to guard against. These are
        a set of PRAW connection errors (timeouts and general connection
        issues) but they can be overridden with a passed-in set.
    :return: None.
    """
    try:
        while True:
            try:
                func(config)
            except exceptions as e:
                logging.warning(
                    '{} - Issue communicating with Reddit. Sleeping for 60s!'
                    ''.format(e)
                )
                time.sleep(60)

    except KeyboardInterrupt:
        logging.info('User triggered shutdown. Shutting down.')
        stop_heartbeat(config)
        sys.exit(0)

    except Exception as e:
        stop_heartbeat(config)
        explode_gracefully(e, config)
