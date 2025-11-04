"""Conformance ranges and helpers.

Reimplements selected parts of mockdown/pruning/conformance.py
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Iterable, List, Sequence, Tuple

import z3  # type: ignore

from cse291p.pipeline.view import IAnchor
from cse291p.pipeline.integration.z3 import anchor_id_to_z3_var


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


def confs_to_bounds(confs: Sequence[Conformance]) -> Dict[str, Fraction]:
    min_w = min(c.w for c in confs)
    max_w = max(c.w for c in confs)
    min_h = min(c.h for c in confs)
    max_h = max(c.h for c in confs)
    min_x = min(c.x for c in confs)
    max_x = max(c.x for c in confs)
    min_y = min(c.y for c in confs)
    max_y = max(c.y for c in confs)
    return {
        'min_w': min_w, 'max_w': max_w,
        'min_h': min_h, 'max_h': max_h,
        'min_x': min_x, 'max_x': max_x,
        'min_y': min_y, 'max_y': max_y,
    }


def add_conf_dims(solver: z3.Optimize, conf: Conformance, confIdx: int, top_dims: Tuple[IAnchor, IAnchor, IAnchor, IAnchor]) -> None:
    """Fix the top-level anchors (x, y, w, h) to the conformance values at index confIdx."""
    top_x, top_y, top_w, top_h = top_dims
    solver.add(anchor_id_to_z3_var(top_w.id, confIdx) == conf.w)
    solver.add(anchor_id_to_z3_var(top_h.id, confIdx) == conf.h)
    solver.add(anchor_id_to_z3_var(top_x.id, confIdx) == conf.x)
    solver.add(anchor_id_to_z3_var(top_y.id, confIdx) == conf.y)


