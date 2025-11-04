"""Types for hierarchical decomposition and Max-SMT solving.

Reimplements:
- mockdown/src/mockdown/pruning/types.py (selected parts)
"""

import operator
from dataclasses import replace
from fractions import Fraction
from typing import Callable, List, TypedDict, Optional, Protocol, Dict, Tuple, Iterable, Any, cast, Sequence, Set

from more_itertools import first_true
from z3 import z3  # type: ignore

from cse291p.pipeline.constraint import IConstraint, ConstraintKind
from cse291p.pipeline.constraint.types import PRIORITY_STRONG
from cse291p.pipeline.integration.z3 import anchor_id_to_z3_var, constraint_to_z3_expr
from cse291p.pipeline.bayes.types import ConstraintCandidate
from cse291p.pipeline.view import IView
from cse291p.types import NT
from .util import anchor_equiv


class ISizeBounds(TypedDict, total=False):
    min_w: Optional[Fraction]
    min_h: Optional[Fraction]
    max_w: Optional[Fraction]
    max_h: Optional[Fraction]
    min_x: Optional[Fraction]
    min_y: Optional[Fraction]
    max_x: Optional[Fraction]
    max_y: Optional[Fraction]


def validate_bounds(bounds: ISizeBounds, view: IView[NT]) -> bool:
    def get(fld: str, default: int) -> Fraction:
        return bounds.get(fld, Fraction(default)) or Fraction(default)

    if view.width < get('min_w', 0): return False
    if view.height < get('min_h', 0): return False
    if view.left < get('min_x', 0): return False
    if view.top < get('min_y', 0): return False
    if view.width > get('max_w', 1 << 30): return False
    if view.height > get('max_h', 1 << 30): return False
    if view.left > get('max_x', 1 << 30): return False
    if view.top > get('max_y', 1 << 30): return False

    return True


def bounds_from_json(it: Dict[Any, Any]) -> ISizeBounds:
    out = {}
    fields = ['min_w', 'min_h', 'max_w', 'max_h', 'min_x', 'max_x', 'min_y', 'max_y']
    for field in fields:
        out[field] = it.get(field)
    return cast(ISizeBounds, out)


class IPruningMethod(Protocol):
    def __call__(self, cns: List[ConstraintCandidate]) -> Tuple[List[IConstraint], Dict[str, Fraction], Dict[str, Fraction]]:
        ...


class BasePruningMethod(IPruningMethod):
    def whole_score(self, c: IConstraint) -> int:
        score = 1
        if c.x_id:
            if c.a.p < 25:
                score *= 10
            if c.a.p < 10:
                score *= 10
            if c.a.p > 100:
                return 1
        if c.b.p < 25:
            score *= 10
        if c.b.p < 10:
            score *= 10
        if c.b.p > 100:
            return score
        return score

    def dump_constraints(self, path: str, view: IView[NT], cns: List[IConstraint]) -> None:
        solver = z3.Optimize()
        self.add_layout_axioms(solver, 0, view, x_dim=True, tracking=False)
        self.add_layout_axioms(solver, 0, view, x_dim=False, tracking=False)
        for ci, c in enumerate(cns):
            solver.assert_and_track(constraint_to_z3_expr(c, 0), f's{str(ci)}')
        with open(path, 'w') as outfile:
            print(solver.sexpr(), file=outfile)
        return

    def make_pairs(self, constraints: List[IConstraint]) -> List[Tuple[IConstraint, IConstraint]]:
        return [(c, cp) for c in constraints for cp in constraints if anchor_equiv(c, cp) and c.op != cp.op]

    def combine_bounds(self, constraints: List[IConstraint]) -> List[IConstraint]:
        output: Set[IConstraint] = set()
        for c in constraints:
            other = first_true(iterable=constraints, pred=lambda t: anchor_equiv(c, t) and c.op != t.op, default=c)
            if other != c and abs(other.b - c.b) < 5:
                output.add(replace(c, op=operator.eq, b=(other.b + c.b) / 2, priority=PRIORITY_STRONG))
            else:
                output.add(c)
        return list(output)

    def merge_pairs(self, pairs: List[Tuple[IConstraint, IConstraint]]) -> List[IConstraint]:
        output: List[IConstraint] = []
        for a, b in pairs:
            if a.b == b.b:
                output.append(replace(a, op=operator.eq))
            else:
                output.append(a)
                output.append(b)
        return output

    def build_biases(self, cands: List[ConstraintCandidate]) -> Dict[IConstraint, float]:
        tiny = 0.000000001
        scores = {x.constraint: max(tiny, x.score) for x in cands}
        min_score = min([x for _, x in scores.items()])
        return {constr: score / min_score + tiny for constr, score in scores.items()}

    def add_containment_axioms(self, solver: z3.Optimize, confIdx: int, parent: IView[NT], x_dim: bool) -> None:
        pl, pr = anchor_id_to_z3_var(parent.left_anchor.id, confIdx), anchor_id_to_z3_var(parent.right_anchor.id, confIdx)
        pt, pb = anchor_id_to_z3_var(parent.top_anchor.id, confIdx), anchor_id_to_z3_var(parent.bottom_anchor.id, confIdx)
        for child in parent.children:
            cl, cr = anchor_id_to_z3_var(child.left_anchor.id, confIdx), anchor_id_to_z3_var(child.right_anchor.id, confIdx)
            ct, cb = anchor_id_to_z3_var(child.top_anchor.id, confIdx), anchor_id_to_z3_var(child.bottom_anchor.id, confIdx)
            if x_dim:
                solver.add(cl >= pl)
                solver.add(cr <= pr)
            else:
                solver.add(ct >= pt)
                solver.add(cb <= pb)
            self.add_containment_axioms(solver, confIdx, child, x_dim)

    def add_layout_axioms(self, solver: z3.Optimize, confIdx: int, boxes: Iterable[IView[NT]], x_dim: bool,
                          tracking: bool = False) -> None:
        for box in boxes:
            w, h = anchor_id_to_z3_var(box.width_anchor.id, confIdx), anchor_id_to_z3_var(box.height_anchor.id, confIdx)
            l, r = anchor_id_to_z3_var(box.left_anchor.id, confIdx), anchor_id_to_z3_var(box.right_anchor.id, confIdx)
            t, b = anchor_id_to_z3_var(box.top_anchor.id, confIdx), anchor_id_to_z3_var(box.bottom_anchor.id, confIdx)
            c_x = anchor_id_to_z3_var(box.center_x_anchor.id, confIdx)
            c_y = anchor_id_to_z3_var(box.center_y_anchor.id, confIdx)
            widthAx = w == (r - l)
            heightAx = h == (b - t)
            if tracking:
                if x_dim:
                    raise Exception('unimplemented')
                solver.assert_and_track(widthAx, f'{box.name}-wax-{str(confIdx)}')
                solver.assert_and_track(heightAx, f'{box.name}-hax-{str(confIdx)}')
                solver.assert_and_track(c_x == (l + r) / 2, f'{box.name}-cx-{str(confIdx)}')
                solver.assert_and_track(c_y == (t + b) / 2, f'{box.name}-cy-{str(confIdx)}')
                for idx, anchor in enumerate(box.anchors):
                    solver.assert_and_track(anchor_id_to_z3_var(anchor.id, confIdx) >= 0,
                                            f'{box.name}-pos-{str(confIdx)}-{str(idx)}')
            else:
                if x_dim:
                    solver.add(widthAx)
                    solver.add(c_x == (l + r) / 2)
                    for anchor in box.x_anchors:
                        solver.add(anchor_id_to_z3_var(anchor.id, confIdx) >= 0)
                else:
                    solver.add(heightAx)
                    solver.add(c_y == (t + b) / 2)
                    for anchor in box.y_anchors:
                        solver.add(anchor_id_to_z3_var(anchor.id, confIdx) >= 0)

    def filter_constraints(self, constraints: List[IConstraint], elim_uneq: bool = True) -> List[IConstraint]:
        constraints = [c for c in constraints if c.kind != ConstraintKind.SIZE_ASPECT_RATIO]
        constraints = self.combine_bounds(constraints)
        if elim_uneq:
            constraints = list(filter(lambda c: c.op == operator.eq, constraints))
        return constraints


PruningMethodFactory = Callable[[List[IView[NT]], ISizeBounds, bool], IPruningMethod]


# Placeholder for hierarchical decomp types

