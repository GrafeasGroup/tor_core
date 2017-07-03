import logging
import re
import sys

import prawcore
import requests

from tor_core import __version__
from tor_core.strings import bot_footer


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


def explode_gracefully(error, config, bot_name=None):
    """
    A last-ditch effort to try to raise a few more flags as it goes down.
    Only call in times of dire need.

    :param bot_name: string; the name of the bot calling the method.
    :param error: an exception object.
    :param tor: the r/ToR helper object
    :return: Nothing. Everything dies here.
    """
    logging.error(error)
    if not bot_name:
        bot_name = config.r.user.me().name
    config.tor.message(
        '{} BROKE - {}'.format(bot_name, error.__class__.__name__.upper()),
        'Please check Bugsnag for the complete error.'
    )
    sys.exit(1)

subreddit_regex = re.compile(
    'reddit.com\/r\/([a-z0-9\-\_\+]+)',
    flags=re.IGNORECASE
)


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
