"""
Exceptions that can be thrown while serializing/deserializing RLP.
"""


class RLPException(Exception):
    """
    Common base class for all RLP exceptions.
    """


class DecodingError(RLPException):
    """
    Indicates that RLP decoding failed.
    """


class EncodingError(RLPException):
    """
    Indicates that RLP encoding failed.
    """
