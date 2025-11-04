"""Stage 3: Constraint Grammar - Define constraint types and representation.

Reimplements:
- mockdown/src/mockdown/constraint/__init__.py (lines 1-6)
"""

from .types import ConstraintKind, IConstraint, Priority, PRIORITY_REQUIRED, PRIORITY_STRONG, PRIORITY_MEDIUM, PRIORITY_WEAK
from .constraint import ConstantConstraint, LinearConstraint
from .factory import ConstraintFactory

__all__ = [
    'ConstraintKind',
    'IConstraint',
    'Priority',
    'PRIORITY_REQUIRED',
    'PRIORITY_STRONG',
    'PRIORITY_MEDIUM',
    'PRIORITY_WEAK',
    'ConstantConstraint',
    'LinearConstraint',
    'ConstraintFactory',
]
