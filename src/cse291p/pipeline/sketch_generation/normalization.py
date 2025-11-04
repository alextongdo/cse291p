"""Constraint normalization utilities for sketch generation.

Reimplements:
- mockdown/src/mockdown/instantiation/normalization.py (lines 1-19)
"""

import dataclasses as dc

from cse291p.pipeline.constraint import IConstraint


def normalize_multiplier(constraint: IConstraint):
    kind = constraint.kind

    if kind.is_constant_form:
        return constraint
    if kind.is_add_only_form:
        return constraint
    if kind.is_general_form:
        raise NotImplementedError()

    return dc.replace(constraint,
                      y_id=constraint.x_id,
                      x_id=constraint.y_id,
                      a=1 / constraint.a)


