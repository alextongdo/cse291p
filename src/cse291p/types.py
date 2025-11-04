"""Type utilities and helpers.

Reimplements:
- mockdown/types.py (lines 1-52)
"""

from __future__ import annotations
from typing import NoReturn, Tuple, TypeVar, Union
import sympy as sym

T = TypeVar('T')

# Type aliases reimplementing mockdown/types.py
AnyNum = Union[int, float]
_ElT = TypeVar('_ElT')
Tuple4 = Tuple[_ElT, _ElT, _ElT, _ElT]

# NT = Numeric Type (reimplements mockdown/types.py line 16)
NT = TypeVar('NT', bound=sym.Number)


def unreachable(x: NoReturn) -> NoReturn:
    """
    This is just like unreachable in any proof assistant.
    
    Reimplements: mockdown/types.py lines 24-49
    """
    assert False, "Unhandled type: {}".format(type(x).__name__)

