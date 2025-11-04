"""Math helpers for noise-tolerant learning.

Reimplements:
- mockdown/src/mockdown/learning/noisetolerant/math.py (entire file)
"""

from fractions import Fraction
from functools import lru_cache
from math import ceil, floor
from typing import Iterable

import numpy as np  # type: ignore


def _continued_fraction(n1: int, n2: int) -> Iterable[int]:
    """Yields the continued fraction expansion of the rationals n1/n2."""
    while n2:
        n1, (term, n2) = n2, divmod(n1, n2)
        yield term


def continued_fraction(a: Fraction) -> Iterable[int]:
    yield from _continued_fraction(a.numerator, a.denominator)


def irrationality(a: Fraction):
    return len(list(continued_fraction(a)))


def sb_depth(a: Fraction):
    return sum(list(continued_fraction(a)))


@lru_cache
def farey(n: int = 100) -> np.ndarray:
    return np.array([Fraction(0, 1)] + sorted({
        Fraction(m, k)
        for k in range(1, n + 1)
        for m in range(1, k + 1)
    }), dtype=object)


@lru_cache
def ext_farey(n: int = 100) -> np.ndarray:
    """Farey sequence with its reversed reciprocals appended (extends to 0-n)."""
    f = farey(n)
    return np.append(f, [1 / a for a in reversed(f[1:-1])])


@lru_cache
def z_ball(center: float, radius: float) -> np.ndarray:
    center, radius = float(center), float(radius)
    return np.arange(ceil(center - radius), floor(center + radius), dtype=int)

"""Mathematical utilities for noise-tolerant learning."""

# Placeholder for math utilities

