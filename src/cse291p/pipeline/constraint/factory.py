"""Constraint factory for creating constraint instances.

Reimplements:
- mockdown/src/mockdown/constraint/factory.py (lines 1-42)
"""

from typing import Any, Optional

from .constraint import ConstantConstraint, LinearConstraint
from .types import ConstraintKind, IComparisonOp, IConstraint
from cse291p.pipeline.view import IAnchorID
from cse291p.types import unreachable

Kind = ConstraintKind


class ConstraintFactory:
    """Factory for creating constraints.
    
    Notes:
        - not an abstract factory (yet). No point.
        - could have some more complex system that doesn't rely on ConstraintKind.
    
    Reimplements: mockdown/src/mockdown/constraint/factory.py lines 11-42
    """

    def __init__(self) -> None:
        """Reimplements: mockdown/src/mockdown/constraint/factory.py lines 18-19"""
        pass

    @staticmethod
    def create(kind: Kind,
               y_id: IAnchorID,
               x_id: Optional[IAnchorID] = None,
               op: Optional[IComparisonOp[Any]] = None) -> IConstraint:
        """Create a constraint based on kind.
        
        Reimplements: mockdown/src/mockdown/constraint/factory.py lines 21-42
        """
        # Note: mypy isn't smart enough to understand `kind in { ... }`.
        # Also, can't use **kwargs for type safety reasons (dataclass will accept None!!!).
        if kind.is_constant_form:
            assert x_id is None

            if op is not None:
                return ConstantConstraint(kind=kind, y_id=y_id, op=op)
            else:
                return ConstantConstraint(kind=kind, y_id=y_id)
        else:
            assert x_id is not None

            if op is not None:
                return LinearConstraint(kind=kind, y_id=y_id, x_id=x_id, op=op)
            else:
                return LinearConstraint(kind=kind, y_id=y_id, x_id=x_id)
