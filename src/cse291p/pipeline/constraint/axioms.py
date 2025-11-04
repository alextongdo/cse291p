"""Axioms for solver integration.

Reimplements:
- mockdown/src/mockdown/constraint/axioms.py (lines 1-13)
"""

from typing import List

import sympy

from cse291p.pipeline.view import IView
from cse291p.types import NT


def make_axioms(views: List[IView[NT]]) -> List[sympy.Expr]:
    """Generate axioms for views.
    
    Reimplements: mockdown/src/mockdown/constraint/axioms.py lines 9-13
    """
    axioms: List[sympy.Expr] = []
    for view in views:
        pass
    return axioms
