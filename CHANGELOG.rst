#####################
Cuttle Pool Changelog
#####################

Here are the changes made to Cuttle Pool for each release.

Version 0.2.1
-------------

- Fix classifier in ``setup.py`` which caused error during upload.

Version 0.2.0
-------------

- PoolConnection and cursors module are importable from cuttlepool instead of
  cuttlepool.cuttlepool.
- ``get_connection()`` will only search for lost connections if it can't get an
  initial connection from the pool or make a connection.
- The connection object in ``get_connection()`` is pinged right before
  returning a ``PoolConnection`` and if the ping fails, the connection is
  replaced.
- ``connection_arguments`` property added which returns a copy of the connection
  arguments.

Version 0.1.0
-------------

Initial release.
