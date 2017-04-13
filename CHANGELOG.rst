#####################
Cuttle Pool Changelog
#####################

Here are the changes made to Cuttle Pool for each release.

Version 0.2.0
-------------

Minor release, unreleased
- PoolConnection and cursors module are importable from cuttlepool instead of
  cuttlepool.cuttlepool.
- ``get_connection()`` will only search for lost connections if it can't get an
  initial connection from the pool or make a connection.
- The connection object in ``get_connection()`` is pinged right before
  returning a ``PoolConnection`` and if the ping fails, the connection is
  replaced.

Version 0.1.0
-------------

Initial release.
