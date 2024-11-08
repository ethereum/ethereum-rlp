"""
Defines the serialization and deserialization format used throughout Ethereum.
"""

from .rlp import RLP, Extended, Simple, decode, decode_to, encode  # noqa: F401

__version__ = "0.1.1"
