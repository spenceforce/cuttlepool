###########
Cuttle Pool
###########

Cuttle Pool is a SQL connection pooling implementation. It's key features are:

Pool overflow
   Creates additional connections if the pool capacity has been reached and
   will remove the overflow when demand for connections decreases.
   
Connection harvesting
   Any connections that haven't been returned to the pool and are no longer
   referenced by anything outside the pool are returned to the pool. This helps
   prevent pool depletion when connections aren't explicitly returned to the
   pool and the connection wrapper is garbage collected.

Connection queuing
   If all else fails and no connection can be immediately found or made, the
   pool will wait a specified amount of time for a connection to be returned
   to the pool before raising an exception.

The intent of Cuttle Pool is to provide a pool implementation for
`Cuttle <https://github.com/smitchell556/cuttle>`_, but it can be used as a
standalone connection pool.

How-to Guide
============

Cuttle Pool is actually pretty easy to use. Just create a ``CuttlePool`` object
and get connections from it. ::

  >>> from cuttlepool import CuttlePool
  >>> pool = CuttlePool(db='ricks_lab', user='rick',
                        passwd='wubalubadubdub', host='localhost')

It's definitely a good idea to import sensitive information (like the user and
password used above) from a separate file that isn't tracked by your VCS.

The ``CuttlePool`` object accepts any parameters that the underlying SQL driver
accepts. There are three other parameters ``CuttlePool`` accepts that are
unrelated to the SQL driver. ``capacity`` sets the max number of connections
the pool will hold at any given time. ``overflow`` sets the max number of
additional connections the pool will create when depleted. All overflow
connections will be closed when returned to the pool if the pool is at
capacity. ``timeout`` sets the amount of time in seconds the pool will wait for
a connection to become free if the pool is depleted when a request for a
connection is made.

A connection from the pool can be used the same way a connection object of the
underlying driver is used. ::

  >>> con = pool.get_connection()
  >>> cur = con.cursor()
  >>> cur.execute('INSERT INTO ricks_lab (invention_name, state) VALUES '
                  '(%s, %s)', ('Space Cruiser', 'damaged'))
  >>> cur.close()
  >>> con.close()

The only exception is calling ``close()`` on the connection. Instead of closing
the connection, it returns it to the pool.

.. note::
   Once ``close()`` is called on the connection object, it renders the
   object useless. The connection object received from the pool is a wrapper
   around the actual connection object and calling ``close()`` on it returns
   the connection to the pool and removes it from the wrapper effectively
   leaving it an empty shell to be garbage collected.

FAQ
===

How do I install it?
--------------------

``pip install cuttlepool``

What SQL implementations does Cuttle Pool support?
--------------------------------------------------

Right now just MySQL using the PyMySQL driver, but this will change in future
versions of Cuttle Pool.

Contributing
------------

It's highly recommended to develop in a virtualenv.

Clone the repository::

  git clone https://github.com/smitchell556/cuttlepool.git

Install the package in editable mode::

  cd cuttlepool
  pip install -e .

Now you're set. See the next section for running tests.

Please work off the ``develop`` branch. Better yet, create a new branch from
``develop`` and merge it back into ``develop`` when functional and passing
tests.

Running the tests
-----------------

To run the tests, tox will need to be installed with ``pip install tox``.

Tests can be run using tox with the command ``tox <sql>`` to run tests that
require a connection to a database, where ``<sql>`` is the specific
implementation desired for testing (such as ``mysql``), or ``tox ambiguous`` to
run tests that do not require a connection to a database. If the tests require
user credentials, create a file ``<sql>_credentials.py`` with the appropriate
variables in the corresponding test directory, where ``<sql>`` is the specific
implementation desired for testing. For example, to run ``tox mysql``,
``USER`` and ``PASSWD`` variables must be placed in a file called
``mysql_credentials.py`` under the ``tests/mysql/`` directory.

Where can I get help?
---------------------

If you haven't read the How-to guide above, please do that first. Otherwise,
check the `issue tracker <https://github.com/smitchell556/cuttlepool/issues>`_.
Your issue may be addressed there and if it isn't please file an issue :)
