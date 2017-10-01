# tor_core

Everything a growing bot needs!

The important parts are two functions that assist with setting up and running the bot.

- `tor_core.initialize.build_bot()` creates the global config object, populates it with settings from Reddit, and also puts together all the local database connections and whatnot.

- `tor_core.helpers.run_until_dead()` does what it says; the official method that replaces all that ugly boilerplate required to start up a bot under the TranscribersOfReddit umbrella. This method handles communication issues with Reddit, timeouts, and handles CTRL+C and unexpected crashes.

When initializing the new bot, all you have to do is call `build_bot()` and then pass your runtime function into `run_until_dead()`. When `run_until_dead()` returns, everything necessary has been processed to allow the bot to die. Set `run_until_dead()` as the last line under `if __name__ == '__main__'` and the bot will exit cleanly after this returns.

## Example

```python
from tor_core.initialize import build_bot
from tor_core.helpers import run_until_dead


def do_your_thing():
    # Do stuff here

    if config.some_configuration == 'value':
        pass  # Do a thing
    else:
        pass  # Do a different thing


def main():
    build_bot('tor_main', __version__, full_name='TranscribersOfReddit')
    config.some_configuration = 'value'
    run_until_dead(do_your_thing)


if __name__ == '__main__':
    main()
```

## Contributing

See [`CONTRIBUTING.md`](/CONTRIBUTING.md) for details.
