"""Constraint implementations (LinearConstraint, ConstantConstraint).

Reimplements:
- mockdown/src/mockdown/constraint/constraint.py (lines 1-122)
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, field, replace
from typing import Any, Dict, Optional, final

import sympy

from .types import ConstraintKind, IComparisonOp, IConstraint, PRIORITY_REQUIRED, Priority, \
    priority_to_str, op_to_str
from cse291p.pipeline.view import IAnchorID


@final
@dataclass(eq=True, frozen=True)
class ConstantConstraint(IConstraint):
    """Constraint of the form y = b.
    
    Reimplements: mockdown/src/mockdown/constraint/constraint.py lines 16-58
    """
    kind: ConstraintKind

    y_id: IAnchorID
    x_id: Optional[IAnchorID] = field(default=None, init=False)

    a: sympy.Rational = field(default=sympy.Rational(0), init=False)
    b: sympy.Rational = sympy.Rational(0)

    op: IComparisonOp[Any] = operator.eq
    priority: Priority = PRIORITY_REQUIRED

    sample_count: int = 0
    is_falsified: bool = False

    def subst(self,
              a: Optional[sympy.Rational] = None,
              b: Optional[sympy.Rational] = None,
              sample_count: int = 1) -> IConstraint:
        """Reimplements: mockdown/src/mockdown/constraint/constraint.py lines 34-41"""
        assert self.is_template
        assert sample_count != 0
        assert a is None or a == 0
        return replace(self, b=b, sample_count=sample_count)

    def __repr__(self) -> str:
        """Reimplements: mockdown/src/mockdown/constraint/constraint.py lines 43-45"""
        b = str(self.b) if not self.is_template else "_"
        return f"{self.y_id} {op_to_str(self.op)} {b}"

    def to_dict(self) -> Dict[str, str]:
        """Reimplements: mockdown/src/mockdown/constraint/constraint.py lines 47-58"""
        return {
            'y': str(self.y_id),
            'op': {
                operator.eq: '=',
                operator.le: '≤',
                operator.ge: '≥'
            }[self.op],
            'b': str(self.b),
            'strength': priority_to_str(self.priority),
            'kind': self.kind.value
        }


@final
@dataclass(eq=True, frozen=True)
class LinearConstraint(IConstraint):
    """Constraint of the form y = a * x + b.
    
    Notes: b may be 0, but a may not be.
    
    Reimplements: mockdown/src/mockdown/constraint/constraint.py lines 63-121
    """
    kind: ConstraintKind

    y_id: IAnchorID
    x_id: IAnchorID

    a: sympy.Rational = sympy.Rational(1)
    b: sympy.Rational = sympy.Rational(0)

    op: IComparisonOp[Any] = operator.eq
    priority: Priority = PRIORITY_REQUIRED

    sample_count: int = 0
    is_falsified: bool = False

    def subst(self,
              a: Optional[sympy.Rational] = None,
              b: Optional[sympy.Rational] = None,
              sample_count: int = 1) -> IConstraint:
        """Reimplements: mockdown/src/mockdown/constraint/constraint.py lines 82-94"""
        assert self.is_template
        assert sample_count != 0

        if a is None:
            a = self.a
        if b is None:
            b = self.b

        return replace(self, a=a, b=b, sample_count=sample_count)

    def __repr__(self) -> str:
        """Reimplements: mockdown/src/mockdown/constraint/constraint.py lines 96-106"""
        a = str(self.a) if not self.is_template else "_"
        b = str(self.b) if not self.is_template else "_"
        op = op_to_str(self.op)

        if self.kind.is_mul_only_form:
            return f"{self.y_id} {op} {a} * {self.x_id}"
        elif self.kind.is_add_only_form:
            return f"{self.y_id} {op} {self.x_id} + {b}"
        else:
            return f"{self.y_id} {op} {a} * {self.x_id} + {b}"

    def to_dict(self) -> Dict[str, str]:
        """Reimplements: mockdown/src/mockdown/constraint/constraint.py lines 108-121"""
        return {
            'y': str(self.y_id),
            'op': {
                operator.eq: '=',
                operator.le: '≤',
                operator.ge: '≥'
            }[self.op],
            'a': str(self.a),
            'x': str(self.x_id),
            'b': str(self.b),
            'strength': priority_to_str(self.priority),
            'kind': self.kind.value
        }
