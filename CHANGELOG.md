# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com) and this
project adheres to [Semantic Versioning](http://semver.org).

## [Unreleased]
### Changed
- Reformat CHANGELOG to be in line with [Keep a
  Changelog](https://keepachangelog.com).
- Instruct users to run tests with `pytest` command.

### Fixed
- Make `setup.py` upload python module instead of package.

## [0.5.0] - 2018-01-04
### Added
- Custom exceptions.

### Changed
- `timeout` argument is now validated for `CuttlePool` initialization.
- Change license from MIT to BSD 3-clause.

### Fixed
- Implemented proper use of `threading.RLock` on a per `CuttlePool`
  instance.

## [0.4.1] - 2017-05-15
### Fixed
- Changed `_normalize_connection()` to a user defined
  `normalize_connection()` method which fixes problems with cross-referenced
  attributes of `Connection` objects.

## [0.4.0] - 2017-05-11 [YANKED]
### Added
- Add ability to set attributes on `PoolConnection`'s underlying connection
  object.

## [0.3.0] - 2017-05-11 [YANKED]
### Added
- `CuttlePool` object now requires a `connect` argument, which is a
  `connect()` method of the chosen sql driver.
- The pool can be emptied with `empty_pool`.
- `_normalize_connection()` will reset all the connection attributes when a
  connection leaves the pool.

### Changed
- Changed `_collect_lost_connections()` to `_harvest_lost_connections()`.
- `get_connection()` now calls `_harvest_lost_connections()` before
  attempting to get a connection from the pool if the pool is empty.
- `CuttlePool` is now meant to be subclassed with user specified function
  `ping()`.
- `get_connection()` will now ping the connection according to a user defined
  function `ping()`.

## [0.2.1] - 2017-04-18
### Fixed
- Fix classifier in `setup.py` which caused error during upload.

## [0.2.0] - 2017-04-18 [YANKED]
### Added
- `connection_arguments` property added which returns a copy of the connection
  arguments.

### Changed
- PoolConnection and cursors module are importable from cuttlepool instead of
  cuttlepool.cuttlepool.
- `get_connection()` will only search for lost connections if it can't get an
  initial connection from the pool or make a connection.
- The connection object in `get_connection()` is pinged right before
  returning a `PoolConnection` and if the ping fails, the connection is
  replaced.

## [0.1.0] - 2017-04-06
### Added
- Initial code.
