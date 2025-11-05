"""Conformance ranges and helpers.

Reimplements selected parts of mockdown/pruning/conformance.py
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Iterable, List, Sequence, Tuple

import z3  # type: ignore

from cse291p.pipeline.view import IAnchor, IView
from cse291p.pipeline.view.primitives import Rect
from cse291p.pipeline.integration.z3 import anchor_id_to_z3_var
from cse291p.pipeline.hierarchical_decomp.util import to_frac
import sympy as sym
from cse291p.types import NT


@dataclass(frozen=True)
class Conformance:
    w: Fraction
    h: Fraction
    x: Fraction
    y: Fraction


def conformance_range(min_conf: Conformance, max_conf: Conformance, scale: int = 5) -> List[Conformance]:
    """Return a small range of conformances from min to max.

    For simplicity (and speed in tests), we return just two endpoints.
    """
    if scale <= 2:
        return [min_conf, max_conf]
    # include a mid-point to help determinism in some cases
    mid = Conformance(
        w=(min_conf.w + max_conf.w) / 2,
        h=(min_conf.h + max_conf.h) / 2,
        x=(min_conf.x + max_conf.x) / 2,
        y=(min_conf.y + max_conf.y) / 2,
    )
    return [min_conf, mid, max_conf]


def confs_to_bounds(min_conf: Conformance, max_conf: Conformance) -> Dict[str, Fraction]:
    """Convert min and max conformances to bounds dictionary.
    
    Reimplements: mockdown/pruning/conformance.py line 37
    """
    return {
        'min_w': min_conf.w, 'max_w': max_conf.w,
        'min_h': min_conf.h, 'max_h': max_conf.h,
        'min_x': min_conf.x, 'max_x': max_conf.x,
        'min_y': min_conf.y, 'max_y': max_conf.y,
    }


def add_conf_dims(solver: z3.Optimize, conf: Conformance, confIdx: int, top_dims: Tuple[IAnchor, IAnchor, IAnchor, IAnchor]) -> None:
    """Fix the top-level anchors (x, y, w, h) to the conformance values at index confIdx."""
    top_x, top_y, top_w, top_h = top_dims
    solver.add(anchor_id_to_z3_var(top_w.id, confIdx) == conf.w)
    solver.add(anchor_id_to_z3_var(top_h.id, confIdx) == conf.h)
    solver.add(anchor_id_to_z3_var(top_x.id, confIdx) == conf.x)
    solver.add(anchor_id_to_z3_var(top_y.id, confIdx) == conf.y)


def to_rect(conf: Conformance) -> Rect[sym.Rational]:
    """Convert a Conformance to a Rect.
    
    Reimplements: mockdown/pruning/conformance.py line 34
    """
    return Rect(
        left=sym.Rational(conf.x),
        top=sym.Rational(conf.y),
        right=sym.Rational(conf.x + conf.w),
        bottom=sym.Rational(conf.y + conf.h)
    )


def conf_zip(conf: Conformance, view: IView[NT]) -> List[Tuple[IAnchor[NT], Fraction]]:
    """Zip a Conformance with a view's anchors.
    
    Reimplements: mockdown/pruning/conformance.py line 109
    """
    return [
        (view.left_anchor, conf.x),
        (view.top_anchor, conf.y),
        (view.width_anchor, conf.w),
        (view.height_anchor, conf.h)
    ]


