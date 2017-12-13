# -*- coding: utf-8 -*-
"""
A mock database driver module.
"""


class MockConnection(object):
    """
    A mock Connection object.

    :param \**kwargs: Accepts anything.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs

        # Used to determine if the connection is "open" or not.
        self.open = True

    def close(self):
        """
        "Closes" the connection.
        """
        self.open = False

    def cursor(self):
        """
        Returns a mock Cursor object.
        """
        return MockCursor(self)


class MockCursor(object):
    """
    A mock Cursor object.

    :param MockConnection connection: A MockConnection object.
    """

    def __init__(self, connection):
        self.connection = connection

    def close(self):
        """
        "Closes" the cursor.
        """
        self.connection = None


def connect(**kwargs):
    """
    Returns a mock Connection object.

    :param \**kwargs: Accepts anything, which is passed to the Connection
                      object.
    """
    return MockConnection(**kwargs)
