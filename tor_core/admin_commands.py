def from_moderator(reply, config):
    return reply.author in config.tor_mods
