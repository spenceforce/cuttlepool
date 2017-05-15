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

Using Cuttle Pool requires subclassing a ``CuttlePool`` object with a user
defined method ``ping()``. ::

  >>> import sqlite3
  >>> from cuttlepool import CuttlePool
  >>> class SQLitePool(CuttlePool):
  ...     def normalize_connection(self, connection):
  ...         connection.row_factory = None
  ...     def ping(self, connection):
  ...         try:
  ...             rv = connection.execute('SELECT 1').fetchall()
  ...             return (1,) in rv
  ...         except sqlite3.Error:
  ...             return False
  >>> pool = SQLitePool(sqlite3.connect, database='ricks_lab')

Let's break this down line by line.

First, the ``sqlite3`` module is imported. ``sqlite3`` will be the underlying
driver.

``CuttlePool`` is imported and subclassed. The ``normalize_connection()``
method takes a ``Connection`` object as a parameter and changes it's
properties. This is important because a ``Connection`` object can be modified
while it's outside of the pool and any modifications made during that time 

Next the ``ping()`` method is implemented, which also takes a ``Connection``
object as a parameter. ``ping()`` ensures the connection is open; if the
connection is open, return ``True`` else return ``False``. In the above
example, a simple statement is executed and if the expected result is returned,
it means the connection is open and ``True`` is returned. The implementation of
this method is really dependent on which driver is being used. If ``pymysql``
was used, the implementation might look like this::

  def ping(self, connection):
      if not connection.open:
          try:
              connection.ping()
          except pymysql.err.Error:
              pass
      return connection.open

Not every driver has the same API, so it's up to the user to implement a
``ping()`` method that works for the chosen driver.

Finally an instance of ``SQLitePool`` is made. The ``sqlite3.connect`` method is
passed to the instance along with the database name. The first argument must be
the ``connect`` method of the sql driver.

The ``CuttlePool`` object and as a result the ``SQLitePool`` object accepts any
parameters that the underlying SQL driver accepts. There are three other
parameters the pool object accepts that are unrelated to the SQL driver.
``capacity`` sets the max number of connections the pool will hold at any given
time. ``overflow`` sets the max number of additional connections the pool will
create when depleted. All overflow connections will be closed when returned to
the pool if the pool is at capacity. ``timeout`` sets the amount of time in
seconds the pool will wait for a connection to become free if the pool is
depleted when a request for a connection is made.

A connection from the pool can be used the same way a connection object of the
underlying driver is used. ::

  >>> con = pool.get_connection()
  >>> cur = con.cursor()
  >>> cur.execute('INSERT INTO garage (invention_name, state) '
                  'VALUES (%s, %s)', ('Space Cruiser', 'damaged'))
  >>> cur.close()
  >>> con.close()

Calling ``close()`` on the connection returns it returns it to the pool instead
of closing it.

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

It supports whatever SQL driver that is passed to it.

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

To run the tests, tox will need to be installed with ``pip install tox`` and
an environment variable, ``TEST_CUTTLE_POOL`` must be set to a SQL type like
``sqlite3`` or ``mysql``.

Tests can be run using tox with the command ``tox``. If the tests require
user credentials, create a file ``<sql>_credentials.py`` with the appropriate
variables in the test directory, where ``<sql>`` is the specific
implementation desired for testing. For example, to run ``tox``,
``USER`` and ``PASSWD`` variables must be placed in a file called
``mysql_credentials.py`` under the ``tests/`` directory.

Where can I get help?
---------------------

If you haven't read the How-to guide above, please do that first. Otherwise,
check the `issue tracker <https://github.com/smitchell556/cuttlepool/issues>`_.
Your issue may be addressed there and if it isn't please file an issue :)
