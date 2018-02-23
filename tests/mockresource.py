# -*- coding: utf-8 -*-
"""
A mock resource module.
"""


class MockResource(object):
    """
    A mock Resource object.

    :param \**kwargs: Accepts anything.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs

        # Used to determine if the resource is "open" or not.
        self.open = True

    def close(self):
        """
        "Closes" the resource.
        """
        self.open = False



def factory(**kwargs):
    """
    Returns a mock Resource object.

    :param \**kwargs: Accepts anything, which is passed to the Resource
        object.
    """
    return MockResource(**kwargs)
