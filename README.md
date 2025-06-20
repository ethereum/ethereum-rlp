Ethereum RLP
============

Recursive-length prefix (RLP) serialization as used by the [Ethereum Execution Layer Specification (EELS)][eels].

[eels]: https://github.com/ethereum/execution-specs

## Usage

Here's a very basic example demonstrating how to define a schema, then encode/decode it:

```python
from dataclasses import dataclass
from ethereum_rlp import encode, decode_to
from ethereum_types.numeric import Uint
from typing import List

@dataclass
class Stuff:
    toggle: bool
    number: Uint
    sequence: List["Stuff"]

encoded = encode(Stuff(toggle=True, number=Uint(3), sequence=[]))
decoded = decode_to(Stuff, encoded)
assert decoded.number == Uint(3)
```

See the `tests/` directory for more examples.
