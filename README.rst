##########
CuttlePool
##########

.. image:: https://travis-ci.org/smitchell556/cuttlepool.svg?branch=master
   :target: https://travis-ci.org/smitchell556/cuttlepool


CuttlePool is a general purpose, thread-safe resource pooling implementation
for use with long lived resources and/or resources that are expensive to
instantiate. It's key features are:

Pool overflow
   Creates additional resources if the pool capacity has been reached and
   will remove the overflow when demand for resources decreases.
   
Resource harvesting
   Any resources that haven't been returned to the pool and are no longer
   referenced by anything outside the pool are returned to the pool. This helps
   prevent pool depletion when resources aren't explicitly returned to the
   pool and the resource wrapper is garbage collected.

Resource queuing
   If all else fails and no resource can be immediately found or made, the
   pool will wait a specified amount of time for a resource to be returned
   to the pool before raising an exception.

How-to Guide
============

Using CuttlePool requires subclassing a ``CuttlePool`` object with a user
defined method ``normalize_resource()`` and ``ping()``. The example below uses
``mysqlclient`` connections as a resource, but CuttlePool is not limited to
connection drivers. ::

  >>> import MySQLdb
  >>> from cuttlepool import CuttlePool
  >>> class MySQLPool(CuttlePool):
  ...     def ping(self, resource):
  ...         try:
  ...             c = resource.cursor()
  ...             c.execute('SELECT 1')
  ...             rv = (1,) in c.fetchall()
  ...             c.close()
  ...             return rv
  ...         except MySQLdb.OperationalError:
  ...             return False
  ...     def normalize_resource(self, resource):
  ...         # For example purposes, but not necessary.
  ...         pass
  >>> pool = MySQLPool(factory=MySQLdb.connect, db='ricks_lab', passwd='aGreatPassword')

Let's break this down line by line.

First, the ``MySQLdb`` module is imported. ``MySQLdb.connect`` will be the
underlying resource factory.

``CuttlePool`` is imported and subclassed. The ``ping()`` method is implemented,
which also takes a resource, the same as ``normalize_resource()``, as a
parameter. ``ping()`` ensures the resource is functional; in this case, it checks
that the ``MySQLdb.Connection`` instance is open. If the resource is functional,
``ping()`` returns ``True`` else it returns ``False``. In the above example, a
simple statement is executed and if the expected result is returned, it means
the resource is open and ``True`` is returned. The implementation of this method
is really dependent on the resource created by the pool and may not even be
necessary.

There is an additional method, ``normalize_resource()``, that can be implemented.
It takes a resource, in this case a ``MySQLdb.Connection`` instance created
by ``MySQLdb.connect``, as a parameter and changes it's properties. This can be
important because a resource can be modified while it's outside of the pool and
any modifications made during that time will persist; this can have unintended
consequences when the resource is later retrieved from the pool. Essentially,
``normalize_connection()`` allows the resource to be set to an expected state
before it is released from the pool for use. Here it does nothing (and in this
case, it's not necessary to define the method), but it's shown for example
purposes.

Finally an instance of ``MySQLPool`` is made. The ``MySQLdb.connect`` method is
passed to the instance along with the database name and password.

The ``CuttlePool`` object and as a result the ``MySQLPool`` object accepts any
parameters that the underlying resource factory accepts as keyword arguments.
There are three other parameters the pool object accepts that are unrelated to
the resource factory. ``capacity`` sets the max number of resources the pool
will hold at any given time. ``overflow`` sets the max number of additional
resources the pool will create when depleted. All overflow resources will be
removed from the pool if the pool is at capacity. ``timeout`` sets the amount
of time in seconds the pool will wait for a resource to become free if the pool
is depleted when a request for a resource is made.

A resource from the pool can be treated the same way as an instance created by
the resource factory passed to the pool. In our example a resource can be used
just like a ``MySQLdb.Connection`` instance. ::

  >>> con = pool.get_resource()
  >>> cur = con.cursor()
  >>> cur.execute(('INSERT INTO garage (invention_name, state) '
  ...              'VALUES (%s, %s)'), ('Space Cruiser', 'damaged'))
  >>> con.commit()
  >>> cur.close()
  >>> con.close()

Calling ``close()`` on the resource returns it to the pool instead of closing
it. It is not necessary to call ``close()`` though. The pool tracks resources
so any unreferenced resources will be collected and returned to the pool. It is
still a good idea to call ``close()`` though, since explicit is better than
implicit.

.. note::
   Once ``close()`` is called on the resource object, it renders the
   object useless. The resource object received from the pool is a wrapper
   around the actual resource object and calling ``close()`` on it returns
   the resource to the pool and removes it from the wrapper effectively
   leaving it an empty shell to be garbage collected.

To automatically "close" resources, ``get_resource()`` can be used in a
``with`` statement. ::

  >>> with pool.get_resource() as con:
  ...     cur = con.cursor()
  ...     cur.execute(('INSERT INTO garage (invention_name, state) '
  ...                  'VALUES (%s, %s)'), ('Space Cruiser', 'damaged'))
  ...     con.commit()
  ...     cur.close()

API
===

The API can be found at `read the docs <https://cuttlepool.readthedocs.io>`_.

FAQ
===

How do I install it?
--------------------

``pip install cuttlepool``

How do I use ``cuttlepool`` with sqlite3?
-----------------------------------------

Don't.

SQLite does not play nice with multiple connections and threads. If you need to
make concurrent writes to a database from multiple connections, consider using a
database with a dedicated server like MySQL, PostgreSQL, etc.

Contributing
------------

It's highly recommended to develop in a virtualenv.

Fork the repository.

Clone the repository::

  git clone https://github.com/<your_username>/cuttlepool.git

Install the package in editable mode::

  cd cuttlepool
  pip install -e .[dev]

Now you're set. See the next section for running tests.

Running the tests
-----------------

Tests can be run with the command ``pytest``.

Where can I get help?
---------------------

If you haven't read the How-to guide above, please do that first. Otherwise,
check the `issue tracker <https://github.com/smitchell556/cuttlepool/issues>`_.
Your issue may be addressed there and if it isn't please file an issue :)
