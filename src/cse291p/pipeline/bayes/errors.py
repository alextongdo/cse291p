"""Learning error types.

Reimplements:
- mockdown/src/mockdown/learning/errors.py (lines 1-8)
"""

from cse291p.pipeline.constraint import IConstraint


class ConstraintFalsified(Exception):
    def __init__(self, constraint: IConstraint):
        self.constraint = constraint


