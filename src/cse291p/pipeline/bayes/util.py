"""Utility helpers for learning.

Reimplements:
- mockdown/src/mockdown/learning/util.py (lines 1-29)
"""

import operator
import sympy
from typing import Any

from cse291p.pipeline.constraint.types import IComparisonOp


def widen_bound(op: IComparisonOp[Any], old: sympy.Number, new: sympy.Number) -> sympy.Number:
    if op == operator.le:
        mx = sympy.Max(old, new)  # type: ignore
        assert isinstance(mx, sympy.Number)
        return mx
    elif op == operator.ge:
        mn = sympy.Min(old, new)  # type: ignore
        assert isinstance(mn, sympy.Number)
        return mn
    else:
        raise Exception("unsupported operator")


def sb_depth(q: sympy.Rational) -> int:
    """Stern-Brocot depth from continued fraction length.

    Reimplements: mockdown/src/mockdown/learning/util.py (sb_depth)
    """
    from sympy import continued_fraction
    return int(sum(continued_fraction(q)))


