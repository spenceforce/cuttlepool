# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com) and this
project adheres to [Semantic Versioning](http://semver.org).

## [0.9.0] - 2019-12-02
### Changed
- Moved logic for iterating over unavailable region to a newly defined
  generator, `_unavailable_range`.
- Dropped support for Python 3.3. This does not mean it won't work for Python
  3.3, but it will no longer be tested.
- Add support for Python 3.7 and 3.8.
- Fix race condition in `get_resource` see [issue #36](https://github.com/smitchell556/cuttlepool/issues/36).

## [0.8.0] - 2018-02-28
### Added
- Public attributes `capacity`, `overflow`, `timeout`, `maxsize`, `size`, and
  `empty` on `CuttlePool` instance.
- Class `_ResourceTracker` for tracking a resource in and out of a pool.
- `PoolFullError`.

### Changed
- `capacity` no longer has a default argument.
- Changed module from connection pool to a general purpose resource pool.
- `PoolConnection` class has been renamed `Resource`.
- `connect` parameter for `CuttlePool` class has been renamed `factory`.
- `connection_arguments` has been renamed `factory_arguments`.
- `get_connection` has been renamed `get_resource`.
- `normalize_connection` has been renamed `normalize_resource`.
- `put_connection` has been renamed `put_resource`.
- Harvest lost resources based on weak references to resource wrappers instead
  of using `sys.getrefcount()` on the resource instances themselves.
- `PoolDepletedError` is now `PoolEmptyError`.
- Use custom queue implementation instead of Python's `queue.Queue` class.

### Removed
- `ConnectionTypeError`, `PoolTypeError` removed.
- `empty_pool()` is no longer usable for general purpose resource pools since
  it's unknown how to teardown a resource.

## [0.7.0] - 2018-02-09
### Added
- `CuttlePool` accepts `PoolConnection` subclasses on instantiation as the
  default connection wrapper.
- `get_connection()` accepts `PoolConnection` subclasses to supersede the
  default connection wrapper.

### Changed
- Make `CAPACITY`, `OVERFLOW`, and `TIMEOUT` "internal" with `_` signifier.
- `_CAPACITY` is now `1`.
- `_OVERFLOW` is now `0`.

## [0.6.0] - 2018-01-28
### Changed
- Reformat CHANGELOG to be in line with [Keep a
  Changelog](https://keepachangelog.com).
- Instruct users to run tests with `pytest` command.
- Make default `CuttlePool` parameters top-level variables.

### Fixed
- `__del__` method calls `empty_pool()` instead of non-existent
  `_close_connections`.

## [0.5.1] - 2018-01-04
### Fixed
- Make `setup.py` upload python module instead of package.

## [0.5.0] - 2018-01-04 [YANKED]
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

## 0.1.0 - 2017-04-06
### Added
- Initial code.

[0.9.0]: https://github.com/smitchell556/cuttlepool/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/smitchell556/cuttlepool/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/smitchell556/cuttlepool/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/smitchell556/cuttlepool/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/smitchell556/cuttlepool/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/smitchell556/cuttlepool/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/smitchell556/cuttlepool/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/smitchell556/cuttlepool/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/smitchell556/cuttlepool/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/smitchell556/cuttlepool/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/smitchell556/cuttlepool/compare/v0.1.0...v0.2.0
