##########
CuttlePool
##########

CuttlePool is a general purpose resource pooling implementation for use with
long lived resources and/or resources that are expensive to instantiate. It's
key features are:

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
``sqlite3`` connections as a resource, but CuttlePool is not limited to
connection drivers. ::

  >>> import sqlite3
  >>> from cuttlepool import CuttlePool
  >>> class SQLitePool(CuttlePool):
  ...     def normalize_resource(self, resource):
  ...         resource.row_factory = None
  ...     def ping(self, resource):
  ...         try:
  ...             rv = resource.execute('SELECT 1').fetchall()
  ...             return (1,) in rv
  ...         except sqlite3.Error:
  ...             return False
  >>> pool = SQLitePool(factory=sqlite3.connect, database='ricks_lab')

Let's break this down line by line.

First, the ``sqlite3`` module is imported. ``sqlite3.connect`` will be the
underlying resource factory.

``CuttlePool`` is imported and subclassed. The ``normalize_resource()``
method takes a resource, in this case a ``sqlite3.Connection`` instance created
by ``sqlite3.connect``, as a parameter and changes it's properties. This is
important because a resource can be modified while it's outside of the pool and
any modifications made during that time will persist; this can have unintended
consequences when the resource is later retrieved from the pool.

Next the ``ping()`` method is implemented, which also takes a resource, the
same as ``normalize_resource()``, as a parameter. ``ping()`` ensures the
resource is functional; in this case, it checks that the ``sqlite3.Connection``
instance is open. If the resource is functional, ``ping()`` returns ``True``
else it returns ``False``. In the above example, a simple statement is executed
and if the expected result is returned, it means the resource is open and
``True`` is returned. The implementation of this method is really dependent on
the resource created by the pool and may not even be necessary.

Finally an instance of ``SQLitePool`` is made. The ``sqlite3.connect`` method is
passed to the instance along with the database name.

The ``CuttlePool`` object and as a result the ``SQLitePool`` object accepts any
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
just like a ``sqlite3.Connection`` instance. ::

  >>> con = pool.get_resource()
  >>> cur = con.cursor()
  >>> cur.execute('INSERT INTO garage (invention_name, state) '
  ...             'VALUES (%s, %s)', ('Space Cruiser', 'damaged'))
  >>> con.commit()
  >>> cur.close()
  >>> con.close()

Calling ``close()`` on the resource returns it to the pool instead of closing
it.

.. note::
   Once ``close()`` is called on the resource object, it renders the
   object useless. The resource object received from the pool is a wrapper
   around the actual resource object and calling ``close()`` on it returns
   the resource to the pool and removes it from the wrapper effectively
   leaving it an empty shell to be garbage collected.

FAQ
===

How do I install it?
--------------------

``pip install cuttlepool``

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
