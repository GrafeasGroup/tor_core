# Changelog

We follow [Semantic Versioning](http://semver.org/) as a way of measuring stability of an update. This
means we will never make a backwards-incompatible change within a major version of the project.

## _[UNRELEASED]_

- Lazy loads redis connection to only when needed (@thelonelyghost)
- Redis connection reads from environment variable `REDIS_CONNECTION_URL`, defaulting to localhost on default redis port (@thelonelyghost)

## v0.2.0

- Added heartbeat web service to check status of a bot (by @itsthejoker)

## v0.1.0

- Created first version of tor_core from parts of u/ToR (by @itsthejoker)
- Added in basic testing suite
