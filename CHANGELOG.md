# Changelog

We follow [Semantic Versioning](http://semver.org/) as a way of measuring stability of an update. This
means we will never make a backwards-incompatible change within a major version of the project.

## _[UNRELEASED]_

Nothing yet...

## v0.4.1 (2017-12-05)

- Heartbeat port filename is read from environment variable to fix concurrency issue with bots (@thelonelyghost)

## v0.4.0 (2017-11-30)

- Adds proper CTRL+C handling (@itsthejoker)
- Changing over to SlackClient (@ngtmeaty)
- Able to bypass domain filters (@itsthejoker)
- Adds support for better API rate limiting from Reddit (@itsthejoker)
- Removes `./bin` scripts in favor of Makefile (dev-only) (@thelonelyghost)
- Adds TravisCI support (@thelonelyghost)
- Removes `addict` dependency (@thelonelyghost)

## v0.3.0 (2017-10-08)

- Adds support for pulling all submissions from specific subreddits (@itsthejoker)

## v0.2.1 (2017-10-04)

- Added Sentry logging support (@itsthejoker)
- Lazy loads redis connection to only when needed (@thelonelyghost)
- Redis connection reads from environment variable `REDIS_CONNECTION_URL`, defaulting to localhost on default redis port (@thelonelyghost)

## v0.2.0

- Added heartbeat web service to check status of a bot (@itsthejoker)

## v0.1.0

- Created first version of tor_core from parts of u/ToR (@itsthejoker)
- Added in basic testing suite
