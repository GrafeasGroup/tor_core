import logging
import os
import random
import sys

from tor_core.helpers import _

import sh


def from_moderator(reply, config):
    return reply.author in config.mods


# XXX: THIS DOES NOT WORK
# but I'm including it anyways because it will be useful if we fix it.
def update_and_restart(reply, config):
    if not from_moderator(reply, config):

        reply.reply(_(random.choice(config.no_gifs)))
        logging.info(
            '{} just issued update. No.'.format(reply.author.name)
        )
    else:
        # update from repo
        sh.git.pull("origin", "master")
        # restart own process
        os.execl(sys.executable, sys.executable, *sys.argv)
