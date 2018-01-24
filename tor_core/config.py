import logging
import os
import random

from praw.models import Subreddit as praw_subreddit

# Load configuration regardless of if bugsnag is setup correctly
try:
    import bugsnag
except ImportError:
    # If loading from setup.py or bugsnag isn't installed, we
    # don't want to bomb out completely
    bugsnag = None

from tor_core import __version__


_missing = object()


# @see https://stackoverflow.com/a/17487613/1236035
class cached_property(object):
    """A decorator that converts a function into a lazy property.  The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value::

        class Foo(object):

            @cached_property
            def foo(self):
                # calculate something important here
                return 42

    The class has to have a `__dict__` in order for this property to
    work.
    """

    # implementation detail: this property is implemented as non-data
    # descriptor. non-data descriptors are only invoked if there is no
    # entry with the same name in the instance's __dict__. this allows
    # us to completely get rid of the access function call overhead. If
    # one chooses to invoke __get__ by hand the property will still work
    # as expected because the lookup logic is replicated in __get__ for
    # manual invocation.

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, _type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


class BaseConfig:
    """
    A base class used for all media-specific settings, e.g.,
    video, audio, image. This is intended to provide a unified
    interface, regardless of the actual media, to ask questions of
    the configuration:

        - What is the formatting string for this media?
        - What domains are whitelisted for this media?

    The inheritance model here is for easy type-checking from tests,
    allowing for validation of an expected interface in a quicker
    manner.

    Specify overridden values on object instantiation for purposes
    of testing and by pulling from remote source (e.g., Reddit Wiki)
    """
    footer = ''


class VideoConfig(BaseConfig):
    """
    Media-specific configuration class for video content
    """
    def __init__(self, format=None):
        self.format = format

    def __repr__(self):
        return self.format


class AudioConfig(BaseConfig):
    """
    Media-specific configuration class for audio content
    """
    def __init__(self, format=None):
        self.format = format

    def __repr__(self):
        return self.format


class ImageConfig(BaseConfig):
    """
    Media-specific configuration class for image content
    """
    def __init__(self, format=None):
        self.format = format

    def __repr__(self):
        return self.format


class OtherContentConfig(BaseConfig):
    """
    Media-specific configuration class for any content that does not
    fit in with the above media types. Articles, mostly.
    """
    def __init__(self, format=None):
        self.format = format

    def __repr__(self):
        return self.format


class Subreddit(praw_subreddit):
    """
    Subreddit base class. Contains all the information needed to handle a
    single subreddit.
    """

    def __init__(
            self,
            reddit_instance=None,  # Required!
            subreddit_name=None,
            bypass_domain_filter=None,
            upvote_filter=None,
            active=True,
            no_link_header=False,
            archive_time=18  # hours
    ):
        self.subreddit_name = subreddit_name
        self.bypass_domain_filter = bypass_domain_filter
        self.upvote_filter = upvote_filter
        self.active = active
        self.no_link_header = no_link_header
        self.archive_time = archive_time
        super(Subreddit, self).__init__(
            reddit_instance, display_name=subreddit_name
        )

    def __repr__(self):
        return self.subreddit_name


class Config(object):
    """
    A singleton object for checking global configuration from
    anywhere in the application
    """

    # Media-specific rules, which are fetchable by a dict key. These
    # are intended to be programmatically accessible based on a
    # parameter given instead of hardcoding the media type in a
    # switch-case style of control structure
    media = {
        'audio': AudioConfig(),
        'video': VideoConfig(),
        'image': ImageConfig(),
        'other': OtherContentConfig(),
    }

    # List of mods of ToR, fetched later using PRAW
    mods = []

    # A collection of Subreddit objects, injected later based on
    # subreddit-specific rules
    subreddits = []
    subreddits_domain_filter_bypass = []

    # API keys for later overwriting based on contents of filesystem
    bugsnag_api_key = None
    slack_api_key = None
    sentry_api_url = None

    # Templating string for the header of the bot post
    header = ''

    perform_header_check = True
    debug_mode = False

    # delay times for removing posts; these are used by u/ToR_archivist
    archive_time_default = None
    archive_time_subreddits = {}

    # Global flag to enable/disable placing the triggers
    # for the OCR bot
    OCR = True

    # Name of the bot
    name = None
    bot_version = '0.0.0'  # this should get overwritten by the bot process
    heartbeat_logging = False

    @cached_property
    def redis(self):
        """
        Lazy-loaded redis connection
        """
        from redis import StrictRedis
        import redis.exceptions

        try:
            url = os.environ.get('REDIS_CONNECTION_URL',
                                 'redis://localhost:6379/0')
            conn = StrictRedis.from_url(url)
            conn.ping()
        except redis.exceptions.ConnectionError:
            logging.fatal("Redis server is not running")
            raise
        return conn

    @cached_property
    def tor(self):
        if self.debug_mode:
            return self.r.subreddit('tor_testing_ground')
        else:
            return self.r.subreddit('transcribersofreddit')

    @cached_property
    def heartbeat_port(self):
        try:
            with open('heartbeat.port', 'r') as port_file:
                port = int(port_file.readline().strip())
            logging.debug('Found existing port saved on disk')
            return port
        except OSError:
            pass

        while True:
            port = random.randrange(40000, 40200)  # is 200 ports too much?
            if self.redis.sismember('active_heartbeat_ports', port) == 0:
                self.redis.sadd('active_heartbeat_ports', port)

                with open('heartbeat.port', 'w') as port_file:
                    port_file.write(str(port))
                logging.debug(
                    'generated port {} and saved to disk'.format(port)
                )

                return port


try:
    Config.bugsnag_api_key = open('bugsnag.key').readline().strip()
except OSError:
    Config.bugsnag_api_key = os.environ.get('BUGSNAG_API_KEY', None)

if bugsnag and Config.bugsnag_api_key:
    bugsnag.configure(
        api_key=Config.bugsnag_api_key,
        app_version=__version__
    )

try:
    Config.slack_api_key = open('slack.key').readline().strip()
except OSError:
    Config.slack_api_key = os.environ.get('SLACK_API_KEY', None)

try:
    Config.sentry_api_url = open('sentry.key').readline().strip()
except OSError:
    Config.sentry_api_url = os.environ.get('SENTRY_API_URL', None)

# ----- Compatibility -----
config = Config()
# config.core_version = __version__
# config.video_domains = []
# config.audio_domains = []
# config.image_domains = []
#
# config.video_formatting = ''
# config.audio_formatting = ''
# config.image_formatting = ''
#
# config.subreddits_to_check = []
# config.upvote_filter_subs = {}
# config.no_link_header_subs = []
#
# config.archive_time_default = 0
# config.archive_time_subreddits = {}
#
# config.tor_mods = []
#
# # section for gifs
# config.no_gifs = []
#
# # enables debug information for the cherrypy heartbeat server
# config.heartbeat_logging = False
