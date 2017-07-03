import logging
import sys
import time

import prawcore

from tor_core.config import config
from tor_core.helpers import explode_gracefully

__version__ = '3.0.0'


default_exceptions = (prawcore.exceptions.RequestException)

def run_until_dead(func, bot_name=None, exceptions=default_exceptions):
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
        sys.exit(0)

    except Exception as e:
        explode_gracefully(e, config, bot_name=bot_name)