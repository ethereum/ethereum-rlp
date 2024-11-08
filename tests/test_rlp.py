import re
from dataclasses import dataclass
from typing import List, Mapping, NoReturn, Sequence, Tuple, Union, cast

import pytest
from ethereum_types.bytes import Bytes, Bytes1, Bytes4, Bytes32
from ethereum_types.numeric import U8, U256, Uint

from ethereum_rlp import Extended, rlp
from ethereum_rlp.exceptions import DecodingError, EncodingError

#
# Tests for RLP encode
#

#
# Testing bytes encoding
#


def test_encode__true() -> None:
    assert rlp.encode(True) == bytearray([0x01])


def test_encode__false() -> None:
    assert rlp.encode(False) == bytearray([0x80])


def test_encode_bytes__empty_bytes() -> None:
    assert rlp.encode_bytes(b"") == bytearray([0x80])
    assert rlp.encode_bytes(bytearray()) == bytearray([0x80])


def test_encode_bytes__single_byte_val_less_than_128() -> None:
    assert rlp.encode_bytes(b"x") == bytearray([0x78])
    assert rlp.encode_bytes(bytearray(b"x")) == bytearray([0x78])


def test_encode_bytes__single_byte_val_equal_128() -> None:
    assert rlp.encode_bytes(b"\x80") == b"\x81\x80"
    assert rlp.encode_bytes(bytearray(b"\x80")) == b"\x81\x80"


def test_encode_bytes__single_byte_val_greater_than_128() -> None:
    assert rlp.encode_bytes(b"\x83") == bytearray([0x81, 0x83])
    assert rlp.encode_bytes(bytearray(b"\x83")) == bytearray([0x81, 0x83])


def test_encode_bytes__55() -> None:
    assert rlp.encode_bytes(b"\x83" * 55) == bytearray([0xB7]) + bytearray(
        b"\x83" * 55
    )
    assert rlp.encode_bytes(bytearray(b"\x83") * 55) == bytearray(
        [0xB7]
    ) + bytearray(b"\x83" * 55)


def test_encode_bytes__large() -> None:
    assert rlp.encode_bytes(b"\x83" * 2**20) == (
        bytearray([0xBA])
        + bytearray(b"\x10\x00\x00")
        + bytearray(b"\x83" * 2**20)
    )
    assert rlp.encode_bytes(bytearray(b"\x83") * 2**20) == (
        bytearray([0xBA])
        + bytearray(b"\x10\x00\x00")
        + bytearray(b"\x83" * 2**20)
    )


#
# Testing dataclass encode/decode
#


@dataclass
class Stuff:
    toggle: bool
    number: Uint
    sequence: List["Stuff"]


def test_encode__dataclass() -> None:
    inner = Stuff(False, Uint(0), [])
    outer = Stuff(True, Uint(255), [inner])
    actual = rlp.encode(outer)
    assert actual == bytes(
        [0xC8, 0x01, 0x81, 0xFF, 0xC4, 0xC3, 0x80, 0x80, 0xC0]
    )


def test_round_trip_dataclass() -> None:
    inner = Stuff(True, Uint(7), [])
    outer = Stuff(False, Uint(14), [inner])
    encoded = rlp.encode(outer)
    decoded = rlp.decode_to(Stuff, encoded)
    assert decoded is not outer
    assert decoded == outer


#
# Testing uint and u256 encoding
#


def test_encode__uint_0() -> None:
    assert rlp.encode(Uint(0)) == b"\x80"


def test_encode__uint_byte_max() -> None:
    assert rlp.encode(Uint(255)) == b"\x81\xff"


def test_encode_Suint256_0() -> None:
    assert rlp.encode(U256(0)) == b"\x80"


def test_encode__uint256_byte_max() -> None:
    assert rlp.encode(U256(255)) == b"\x81\xff"


#
# Testing str encoding
#


def test_encode__empty_str() -> None:
    assert rlp.encode("") == b"\x80"


def test_encode__one_char_str() -> None:
    assert rlp.encode("h") == b"h"


def test_encode__multi_char_str() -> None:
    assert rlp.encode("hello") == b"\x85hello"


#
# Testing sequence encoding
#


def test_encode_sequence__empty() -> None:
    assert rlp.encode_sequence([]) == bytearray([0xC0])


def test_encode_sequence__single_elem_list_byte() -> None:
    assert rlp.encode_sequence([b"hello"]) == bytearray([0xC6]) + b"\x85hello"


def test_encode_sequence__single_elem_list_uint() -> None:
    assert rlp.encode_sequence([Uint(255)]) == bytearray([0xC2]) + b"\x81\xff"


def test_encode_sequence___10_elem_byte_uint_combo() -> None:
    raw_data = [b"hello"] * 5 + [Uint(35)] * 5
    expected = (
        bytearray([0xE3])
        + b"\x85hello\x85hello\x85hello\x85hello\x85hello#####"
    )
    assert rlp.encode_sequence(raw_data) == expected


def test_encode_sequence__20_elem_byte_uint_combo() -> None:
    raw_data = [Uint(35)] * 10 + [b"hello"] * 10
    expected = (
        bytearray([0xF8])
        + b"F"
        + b"##########\x85hello\x85hello\x85hello\x85hello\x85hello\x85hello\x85hello\x85hello\x85hello\x85hello"
    )
    assert rlp.encode_sequence(raw_data) == expected


def test_encode_sequence__nested() -> None:
    nested_sequence: Sequence["Extended"] = [
        b"hello",
        Uint(255),
        [b"how", [b"are", b"you", [b"doing"]]],
    ]
    expected: Bytes = (
        b"\xdd\x85hello\x81\xff\xd4\x83how\xcf\x83are\x83you\xc6\x85doing"
    )
    assert rlp.encode_sequence(nested_sequence) == expected


def test_encode__successfully() -> None:
    test_cases: List[Tuple[rlp.Extended, Union[bytes, bytearray]]] = [
        (b"", bytearray([0x80])),
        (b"\x83" * 55, bytearray([0xB7]) + bytearray(b"\x83" * 55)),
        (Uint(0), b"\x80"),
        (Uint(255), b"\x81\xff"),
        ([], bytearray([0xC0])),
        (
            [b"hello"] * 5 + [Uint(35)] * 5,
            bytearray([0xE3])
            + bytearray(b"\x85hello\x85hello\x85hello\x85hello\x85hello#####"),
        ),
        (
            [b"hello", Uint(255), [b"how", [b"are", b"you", [b"doing"]]]],
            bytearray(
                b"\xdd\x85hello\x81\xff\xd4\x83how\xcf\x83are\x83you\xc6\x85doing"
            ),
        ),
    ]
    for raw_data, expected_encoding in test_cases:
        assert rlp.encode(raw_data) == expected_encoding


def test_encode__fails() -> None:
    test_cases = [
        123,
        [b"hello", Uint(255), [b"how", [b"are", [b"you", [123]]]]],
    ]
    for raw_data in test_cases:
        with pytest.raises(EncodingError):
            rlp.encode(cast(Extended, raw_data))


#
# Tests for RLP decode
#

#
# Testing bytes decoding
#


def test_decode_to_bytes__empty() -> None:
    assert rlp.decode_to_bytes(bytearray([0x80])) == b""


def test_decode_to_bytes__single_byte_less_than_128() -> None:
    assert rlp.decode_to_bytes(bytearray([0])) == bytearray([0])
    assert rlp.decode_to_bytes(bytearray([0x78])) == bytearray([0x78])


def test_decode_to_bytes__single_byte_gte_128() -> None:
    assert rlp.decode_to_bytes(bytearray([0x81, 0x83])) == b"\x83"
    assert rlp.decode_to_bytes(b"\x81\x80") == b"\x80"


def test_decode_to_bytes__55() -> None:
    encoding = bytearray([0xB7]) + bytearray(b"\x83" * 55)
    expected_raw_data = bytearray(b"\x83") * 55
    assert rlp.decode_to_bytes(encoding) == expected_raw_data


def test_decode_to_bytes__large() -> None:
    encoding = bytearray([0xBA]) + b"\x10\x00\x00" + b"\x83" * (2**20)
    expected_raw_data = b"\x83" * (2**20)
    assert rlp.decode_to_bytes(encoding) == expected_raw_data


def test_decode_to_bytes__out_of_bounds() -> None:
    with pytest.raises(DecodingError, match="truncated"):
        rlp.decode_to_bytes(b"\x84")


def test_decode_to_bytes__single_byte_sequence() -> None:
    # Honestly, I don't really understand this one.
    with pytest.raises(DecodingError):
        rlp.decode_to_bytes(b"\x81\x79")


def test_decode_to_bytes__long_missing_length() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_to_bytes(b"\xb8")


def test_decode_to_bytes__long_zero() -> None:
    input = b"\xBA\x00\x00\x00" + (b"\x83" * 2**20)
    with pytest.raises(DecodingError):
        rlp.decode_to_bytes(input)


def test_decode_to_bytes__long_too_short() -> None:
    input = b"\xB8\x37\x00\x00" + (b"\x83" * 2**20)
    with pytest.raises(DecodingError):
        rlp.decode_to_bytes(input)


def test_decode_to_bytes__long_out_of_bounds() -> None:
    input = b"\xBA\x37\x00\x00"
    with pytest.raises(DecodingError):
        rlp.decode_to_bytes(input)


def test_decode_to__bytes() -> None:
    expected = bytes(b"\x83" * 55)
    input = bytes([0xB7]) + expected
    actual = rlp.decode_to(bytes, input)
    assert isinstance(actual, bytes)
    assert expected == actual


@dataclass
class WithInt:
    items: int


def test_decode_to__int() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_to(WithInt, b"\xc1\x00")


def test_decode_to__dataclass_bytes_not_sequence() -> None:
    with pytest.raises(DecodingError, match="got `bytes`"):
        rlp.decode_to(Stuff, b"\x80")


def test_decode_to__dataclass_field_count() -> None:
    match = re.escape("`Stuff` needs 3 field(s), but got 1 instead")
    with pytest.raises(DecodingError, match=match):
        rlp.decode_to(Stuff, b"\xc1\x80")


def test_decode_to__bool_invalid() -> None:
    with pytest.raises(DecodingError, match="invalid boolean"):
        rlp.decode_to(bool, b"\x05")


def test_decode_to__bytes_sequence() -> None:
    with pytest.raises(DecodingError, match="invalid bytes"):
        rlp.decode_to(bytes, b"\xc0")


def test_decode_to__fixed_bytes_invalid_len() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_to(Bytes32, b"\x80")


def test_decode_to__uint_sequence() -> None:
    with pytest.raises(DecodingError, match="invalid uint"):
        rlp.decode_to(Uint, b"\xc0")


def test_decode_to__u8_invalid_len() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_to(U8, b"\x82\x01\xff")


@dataclass
class WithUnion:
    union: Union[Bytes1, bool]


def test_decode_to__union_left() -> None:
    actual = rlp.decode_to(WithUnion, b"\xc1\x78")
    expected = WithUnion(Bytes1(b"x"))
    assert isinstance(actual.union, Bytes1)
    assert actual == expected


def test_decode_to__union_right() -> None:
    actual = rlp.decode_to(WithUnion, b"\xc1\x80")
    expected = WithUnion(False)
    assert isinstance(actual.union, bool)
    assert actual == expected


def test_decode_to__union_neither() -> None:
    with pytest.raises(DecodingError, match="no matching union variant"):
        rlp.decode_to(WithUnion, b"\xc3\x82\x05\x04")


def test_decode_to__union_both() -> None:
    with pytest.raises(DecodingError, match="multiple matching union variant"):
        rlp.decode_to(WithUnion, b"\xc1\x01")


@dataclass
class WithTuple:
    items: Tuple[Uint, Bytes4]


def test_decode_to__tuple() -> None:
    actual = rlp.decode_to(WithTuple, b"\xc7\xc6\x05\x84\x01\x02\x03\x04")
    expected = WithTuple((Uint(5), Bytes4(b"\x01\x02\x03\x04")))
    assert isinstance(actual.items, tuple)
    assert actual == expected


def test_decode_to__tuple_bytes() -> None:
    with pytest.raises(DecodingError, match="invalid tuple"):
        rlp.decode_to(WithTuple, b"\xc1\x79")


@dataclass
class WithEllipsis:
    items: Tuple[Uint, ...]


def test_decode_to__tuple_ellipsis() -> None:
    actual = rlp.decode_to(WithEllipsis, b"\xc6\xc5\x01\x02\x03\x04\x05")
    expected = WithEllipsis((Uint(1), Uint(2), Uint(3), Uint(4), Uint(5)))
    assert isinstance(actual.items, tuple)
    assert actual == expected


@dataclass
class WithNoReturn:
    no_return: NoReturn


def test_decode_to__missing_origin() -> None:
    with pytest.raises(Exception, match="NoReturn"):
        rlp.decode_to(WithNoReturn, b"\xc1\x05")


@dataclass
class WithNonRlp:
    item: Tuple[Mapping[int, int]]


def test_decode_to__annotation_non_rlp() -> None:
    with pytest.raises(DecodingError, match="RLP non-type"):
        rlp.decode_to(WithNonRlp, b"\xc2\xc1\x01")


@dataclass
class WithList:
    items: List[Union[Bytes1, Bytes4]]


def test_decode_to__list_bytes() -> None:
    with pytest.raises(DecodingError, match="invalid list"):
        rlp.decode_to(WithList, b"\xc1\x80")


def test_decode_to__list_invalid_union() -> None:
    with pytest.raises(DecodingError, match="list item 0"):
        rlp.decode_to(WithList, b"\xc2\xc1\xc0")


#
# Testing uint decoding
#


def test_decode__to_zero_uint() -> None:
    assert rlp.decode(b"\x80") == Uint(0).to_be_bytes()


def test_decode__to_255_uint() -> None:
    assert rlp.decode(b"\x81\xff") == Uint(255).to_be_bytes()


#
# Testing string decoding
#


def test_decode__empty_str() -> None:
    assert rlp.decode(b"\x80") == "".encode()


def test_decode__one_char_str() -> None:
    assert rlp.decode(b"h") == "h".encode()


def test_decode__multi_char_str() -> None:
    assert rlp.decode(b"\x85hello") == "hello".encode()


#
# Testing sequence decoding
#


def test_decode_to_sequence__empty() -> None:
    assert rlp.decode_to_sequence(bytearray([0xC0])) == []


def test_decode_to_sequence__1_elem_sequence_of_byte() -> None:
    assert rlp.decode_to_sequence(bytearray([0xC6]) + b"\x85hello") == [
        b"hello"
    ]


def test_decode_to_sequence__1_elem_sequence_of_uint() -> None:
    assert rlp.decode_to_sequence(bytearray([0xC2]) + b"\x81\xff") == [
        Uint(255).to_be_bytes()
    ]


def test_decode_to_sequence__10_elem_sequence_of_bytes_and_uints() -> None:
    encoded_data = (
        bytearray([0xE3])
        + b"\x85hello\x85hello\x85hello\x85hello\x85hello#####"
    )
    expected_raw_data = [b"hello"] * 5 + [Uint(35).to_be_bytes()] * 5
    assert rlp.decode_to_sequence(encoded_data) == expected_raw_data


def test_decode_to_sequence__20_elem_sequence_of_bytes_and_uints() -> None:
    encoded_data = (
        bytearray([0xF8])
        + b"F"
        + b"\x85hello\x85hello\x85hello\x85hello\x85hello\x85hello\x85hello\x85hello\x85hello\x85hello##########"
    )
    expected_raw_data = [b"hello"] * 10 + [Uint(35).to_be_bytes()] * 10
    assert rlp.decode_to_sequence(encoded_data) == expected_raw_data


def test_decode_to_sequence__nested() -> None:
    encoded_data = (
        b"\xdf\x85hello\x81\xff\xd6\x83how\xd1\x83are\x83you\xc8\x85doing\xc1#"
    )
    expected_raw_data = [
        b"hello",
        Uint(255).to_be_bytes(),
        [
            b"how",
            [b"are", b"you", [b"doing", [Uint(35).to_be_bytes()]]],
        ],
    ]
    assert rlp.decode_to_sequence(encoded_data) == expected_raw_data


def test_decode_to_sequence__out_of_bounds_item() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_to_sequence(b"\xc1\x81")


def test_decode_to_sequence__out_of_bounds() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_to_sequence(b"\xc1")


def test_decode_to_sequence__long_missing_length() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_to_sequence(b"\xf8")


def test_decode_to_sequence__long_zero() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_to_sequence(b"\xf8\x00")


def test_decode_to_sequence__long_too_short() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_to_sequence(b"\xf8\x37" + (b"\x00" * 0x37))


def test_decode_to_sequence__long_out_of_bounds() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_to_sequence(b"\xf8\x39")


def test_decode__successfully() -> None:
    test_cases = [
        (bytearray([0x80]), bytearray()),
        (bytearray([0xB7]) + bytearray(b"\x83" * 55), bytearray(b"\x83") * 55),
        (bytearray([0xC0]), []),
        (
            b"\xdb\x85hello\xd4\x83how\xcf\x83are\x83you\xc6\x85doing",
            [b"hello", [b"how", [b"are", b"you", [b"doing"]]]],
        ),
    ]
    for encoding, expected_raw_data in test_cases:
        assert rlp.decode(encoding) == expected_raw_data


def test_decode__failure_empty_bytes() -> None:
    with pytest.raises(DecodingError):
        rlp.decode(b"")


def test_round_trip_encoding_and_decoding() -> None:
    test_cases: List[Extended] = [
        b"",
        b"h",
        b"hello how are you doing today?",
        Uint(35).to_be_bytes(),
        Uint(255).to_be_bytes(),
        [],
        [
            b"hello",
            [b"how", [b"are", b"you", [b"doing", [Uint(255).to_be_bytes()]]]],
        ],
        [[b"hello", b"world"], [b"how", b"are"], [b"you", b"doing"]],
    ]
    for raw_data in test_cases:
        assert rlp.decode(rlp.encode(raw_data)) == raw_data


def test_decode_item_length__empty() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_item_length(b"")


def test_decode_item_length__long() -> None:
    actual = rlp.decode_item_length(b"\xbf" + b"\x01" + b"\x00" * 7)
    expected = 0x0100000000000000 + 1 + 8
    assert actual == expected


def test_decode_item_length__long_length_out_of_bounds() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_item_length(b"\xbf" + b"\x01" + b"\x00" * 6)


def test_decode_item_length__long_length_too_short() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_item_length(b"\xbf" + b"\x00" + b"\x00" * 7)


def test_decode_item_length__long_long_length_too_short() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_item_length(b"\xf8" + b"\x00" + b"\x00" * 7)


def test_decode_item_length__long_long_length_out_of_bounds() -> None:
    with pytest.raises(DecodingError):
        rlp.decode_item_length(b"\xf9" + b"\x01")


def test_decode_item_length__long_long() -> None:
    # TODO: I have no idea if the 0xf8 - 0xff range is meant to work this way.
    actual = rlp.decode_item_length(b"\xf8" + b"\xff")
    expected = 0xFF + 1 + 1
    assert actual == expected
