import os

__version__ = "1.0.0"


# ========================
# | GLOBAL BOT VARIABLES |
# ========================

# This is where we retrieve all the metadata used across all of the bots. We
# should defer to environment variables to override with sane defaults if no
# values are given.

# Task broker URL for specifying what backend to configure to hold the queues
__BROKER_URL__ = os.getenv("TASK_BROKER", "redis://localhost:6379/1")

# The python module reference where the celery app config is held for the entire
# network of all running bots. This module should be able to be imported.
CELERY_CONFIG_MODULE = os.getenv("CELERY_CONFIG_MODULE", "tor_worker.celeryconfig")

# Comma-separated values for names of bots we control
OUR_BOTS = os.getenv(
    "TOR_BOT_USERNAMES", "transcribersofreddit,transcribot,tor_archivist"
).split(",")
OUR_BOTS = [name.strip() for name in OUR_BOTS if name.strip()]

# Defaults to look for admin commands in the `tor.admin_commands` module
ADMIN_COMMAND_PKG = os.getenv("TOR_ADMIN_COMMAND_MODULE", "tor")


# ===================
# | Default Objects |
# ===================

# These are objects which should be used almost as if they are a part of the
# Python standard library

_missing = object()


# @see https://stackoverflow.com/a/17487613/1236035
class cached_property(object):  # pragma: no cover
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
