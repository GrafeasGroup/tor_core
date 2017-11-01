[![Waffle.io - Columns and their card count](https://badge.waffle.io/TranscribersOfReddit/TranscribersOfReddit.svg?columns=all)](http://waffle.io/TranscribersOfReddit/TranscribersOfReddit)

# Transcribers Of Reddit (core)

This package acts as a framework for shared functionality among all of the bots acting on /r/TranscribersOfReddit.
The hope is that using this framework will reduce the overhead for keeping consistent names and configurations that
are used across all or most of the bots. It is also helpful for setting up and tearing down each bot to run in
daemon mode.

Here are the important parts:

- `tor_core.initialize.build_bot()` scaffolds out the initial configuration for the bot, populating it with settings from Reddit, database connections, etc.
- `tor_core.helpers.run_until_dead()` does what it says; the official method that replaces all that ugly boilerplate required to start up and keep a bot running through all of the exceptions, timeouts and unexpected crashes.

## Example

When initializing the new bot, call `build_bot()` and then pass the name of the function which handles what your bot
will be doing into `run_until_dead()`. Even if an error occurs or the bot is told to shut down (e.g., sending `Ctrl-C`)
it will clean up its own mess and shut down cleanly.

Here's a concrete example:

```python
from tor_core.config import config  # Our global configuration object
from tor_core.initialize import build_bot
from tor_core.helpers import run_until_dead


def do_your_thing():
    # Do stuff here

    if config.some_configuration == 'value':
        pass  # Do a thing
    else:
        pass  # Do a different thing


def main():
    # Initial scaffolding out of the bot
    build_bot('tor_main', __version__, full_name='TranscribersOfReddit')

    # Bot-specific customizations before starting
    config.some_configuration = 'value'

    # Long running process which blocks until a kill-signal is sent
    run_until_dead(do_your_thing)


if __name__ == '__main__':
    main()
```

## Contributing

See [`CONTRIBUTING.md`](/CONTRIBUTING.md) for details.
