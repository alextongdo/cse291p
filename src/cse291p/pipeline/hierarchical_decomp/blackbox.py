"""Max-SMT solving via BlackBoxPruner.

Reimplements:
- mockdown/src/mockdown/pruning/blackbox.py (BlackBoxPruner parts)
"""

import operator
from dataclasses import replace
from enum import Enum
from fractions import Fraction
from typing import Dict, List, Set, Tuple, Optional, Any, Generic, Sequence, Iterator, FrozenSet, cast, Iterable, ItemsView

import sympy as sym
import z3  # type: ignore

from cse291p.pipeline.constraint import IConstraint, ConstraintKind
from cse291p.pipeline.constraint.constraint import ConstantConstraint
from cse291p.pipeline.constraint.types import PRIORITY_STRONG
from cse291p.pipeline.integration.z3 import constraint_to_z3_expr, anchor_id_to_z3_var, extract_model_valuations
from cse291p.pipeline.bayes.types import ConstraintCandidate
from cse291p.pipeline.view import IView, IAnchor
from cse291p.pipeline.view.primitives import h_attrs, v_attrs, Attribute
from .conformance import Conformance, confs_to_bounds, conformance_range, add_conf_dims
from .types import ISizeBounds, BasePruningMethod
from .util import short_str, to_frac
from cse291p.types import unreachable, NT

import logging

logger = logging.getLogger(__name__)


def is_x_constr(c: IConstraint) -> bool:
    hs_attrs = h_attrs | {Attribute.WIDTH}
    vs_attrs = v_attrs | {Attribute.HEIGHT}
    if c.x_id:
        if c.x_id.attribute in hs_attrs and c.y_id.attribute in hs_attrs:
            return True
        elif c.x_id.attribute in vs_attrs and c.y_id.attribute in vs_attrs:
            return False
        else:
            print(short_str(c))
            raise Exception('bad constraint with mixed dimensions')
    else:
        return c.y_id.attribute in hs_attrs


LogLevel = Enum('LogLevel', 'NONE ALL')


class BlackBoxPruner(BasePruningMethod, Generic[NT]):
    example: IView[NT]
    top_width: IAnchor[NT]
    top_height: IAnchor[NT]
    top_x: IAnchor[NT]
    top_y: IAnchor[NT]
    solve_unambig: bool
    log_level: LogLevel

    def __init__(self, examples: Sequence[IView[NT]], bounds: ISizeBounds, solve_unambig: bool, targets: Optional[Sequence[IView[NT]]] = None):
        bounds_frac = {k: to_frac(v) if v else None for k, v in cast(ItemsView[str, Optional[Fraction]], bounds.items())}

        heights = [to_frac(v.height) for v in examples]
        widths = [to_frac(v.width) for v in examples]
        xs = [to_frac(v.left) for v in examples]
        ys = [to_frac(v.top) for v in examples]

        min_w = min(bounds_frac.get('min_w', None) or min(widths), min(widths))
        max_w = max(bounds_frac.get('max_w', None) or max(widths), max(widths))
        min_h = min(bounds_frac.get('min_h', None) or min(heights), min(heights))
        max_h = max(bounds_frac.get('max_h', None) or max(heights), max(heights))

        min_x = min(bounds_frac.get('min_x', None) or min(xs), min(xs))
        max_x = max(bounds_frac.get('max_x', None) or max(xs), max(xs))
        min_y = min(bounds_frac.get('min_y', None) or min(ys), min(ys))
        max_y = max(bounds_frac.get('max_y', None) or max(ys), max(ys))

        self.min_conf = Conformance(min_w, min_h, min_x, min_y)
        self.max_conf = Conformance(max_w, max_h, max_x, max_y)

        assert len(examples) > 0, "Pruner requires non-empty learning examples"

        self.example = examples[0]

        self.top_width = self.example.width_anchor
        self.top_height = self.example.height_anchor
        self.top_x = self.example.left_anchor
        self.top_y = self.example.top_anchor

        self.targets: Sequence[IView[NT]] = targets or [x for x in self.example]
        self.solve_unambig = solve_unambig
        self.log_level = LogLevel.NONE

    def add_determinism(self, solver: z3.Optimize, cmap: Dict[str, IConstraint], x_dim: bool) -> None:
        constrs_by_id: Dict[str, List[Tuple[str, IConstraint]]] = {str(a.id): [] for box in self.targets for a in box.anchors if box.name != self.example.name}
        for z3_name, constr in cmap.items():
            if constr.y_id.view_name == self.example.name:
                continue
            key = str(constr.y_id)
            constrs_by_id[key].append((z3_name, constr))

        for yid, constrs in constrs_by_id.items():
            sum_prefix = "unique_var_" + yid
            summand = z3.IntVal(0)
            for idx, cnstrs in enumerate(constrs):
                z3_name = cnstrs[0]
                item_var = z3.Int(sum_prefix + str(idx))
                solver.add(z3.Implies(z3.Bool(z3_name), item_var == 1))
                solver.add(z3.Implies(z3.Not(z3.Bool(z3_name)), item_var == 0))
                summand = summand + item_var
            solver.add(summand <= 1)

        for box in self.targets:
            if box.name == self.example.name:
                continue
            if x_dim:
                xdims = [box.left_anchor, box.right_anchor, box.width_anchor, box.center_x_anchor]
                sum_prefix = "determ_x_" + box.name
                summand = z3.IntVal(0)
                vidx = 0
                for var in xdims:
                    for cnstrs in constrs_by_id[str(var.id)]:
                        z3_name = cnstrs[0]
                        item_var = z3.Int(sum_prefix + str(vidx))
                        solver.add(z3.Implies(z3.Bool(z3_name), item_var == 1))
                        solver.add(z3.Implies(z3.Not(z3.Bool(z3_name)), item_var == 0))
                        summand = summand + item_var
                        vidx += 1
                solver.add(summand == 2)
            else:
                ydims = [box.top_anchor, box.bottom_anchor, box.height_anchor, box.center_y_anchor]
                sum_prefix = "determ_y_" + box.name
                summand = z3.IntVal(0)
                vidx = 0
                for var in ydims:
                    for cnstrs in constrs_by_id[str(var.id)]:
                        z3_name = cnstrs[0]
                        item_var = z3.Int(sum_prefix + str(vidx))
                        solver.add(z3.Implies(z3.Bool(z3_name), item_var == 1))
                        solver.add(z3.Implies(z3.Not(z3.Bool(z3_name)), item_var == 0))
                        summand = summand + item_var
                        vidx += 1
                solver.add(summand == 2)

    def add_conf_dims(self, solver: z3.Optimize, conf: Conformance, confIdx: int) -> None:
        return add_conf_dims(solver, conf, confIdx, (self.top_x, self.top_y, self.top_width, self.top_height))

    def synth_unambiguous(self, solver: z3.Optimize, names_map: Dict[str, IConstraint], confs: List[Conformance], x_dim: bool, dry_run: bool) -> Tuple[List[IConstraint], Dict[str, Fraction], Dict[str, Fraction]]:
        solver.push()
        invalid_candidates: Set[FrozenSet[str]] = set()
        iters = 0

        def get_ancs(v: IView[NT]) -> List[IAnchor[NT]]:
            return v.x_anchors if x_dim else v.y_anchors

        while True:
            for invalid_cand in invalid_candidates:
                control_term = z3.BoolVal(True)
                for control in invalid_cand:
                    control_term = z3.And(control_term, z3.Bool(control))
                solver.add(z3.Not(control_term))
            if self.log_level == LogLevel.ALL:
                with open("debug-%s-invalids-%d.smt2" % (self.example.name, iters), 'w') as debugout:
                    print(solver.sexpr(), file=debugout)

            if (solver.check() == z3.sat):
                constr_decls = [v for v in solver.model().decls() if v.name() in names_map]
                new_cand = frozenset([v.name() for v in constr_decls if solver.model().get_interp(v)])
                old_model = solver.model()
                solver.pop(); solver.push()

                for control in new_cand:
                    solver.add(z3.Bool(control))

                conf_idx = len(confs) // 2
                names = [str(a.id) for box in [self.example] + list(self.targets) for a in get_ancs(box)]
                vals = extract_model_valuations(old_model, conf_idx, names)
                for p_anc in get_ancs(self.example):
                    concrete_value = vals[str(p_anc.id)]
                    solver.add(anchor_id_to_z3_var(p_anc.id, conf_idx) == concrete_value)

                placement_term = z3.BoolVal(True)
                for child in self.targets:
                    if child.name == self.example.name:
                        continue
                    for c_anc in get_ancs(child):
                        concrete_value = vals[str(c_anc.id)]
                        placement_term = z3.And(placement_term, anchor_id_to_z3_var(c_anc.id, conf_idx) == concrete_value)
                solver.add(z3.Not(placement_term))

                if dry_run or solver.check() == z3.unsat:
                    if self.log_level != LogLevel.NONE:
                        print('took %d iters' % iters)
                    constr_decls = [v for v in old_model.decls() if v.name() in names_map]
                    output = [names_map[v.name()] for v in constr_decls if old_model.get_interp(v)]
                    names = [str(a.id) for box in [self.example] + list(self.targets) for a in get_ancs(box)]
                    min_vals, max_vals = extract_model_valuations(old_model, 0, names), extract_model_valuations(old_model, len(confs) - 1, names)
                    return (output, min_vals, max_vals)
                elif solver.check() == z3.sat:
                    if new_cand in invalid_candidates:
                        raise Exception('inconceivable')
                    invalid_candidates.add(new_cand)
                    solver.pop(); solver.push()
                    iters += 1
                    continue
                else:
                    print('unknown?', solver.check())
                    raise Exception('unexpected solver output')
            else:
                with open("unsat-%s.smt2" % self.example.name, 'w') as debugout:
                    print(solver.sexpr(), file=debugout)
                raise Exception('cant find a solution')

    def reward_parent_relative(self, biases: Dict[IConstraint, float]) -> Dict[IConstraint, float]:
        for constr, score in biases.items():
            if constr.x_id:
                yv = self.example.find_anchor(constr.y_id)
                if yv and yv.view.is_parent_of_name(constr.x_id.view_name):
                    biases[constr] = score * 10
        return biases

    def __call__(self, cands: List[ConstraintCandidate]) -> Tuple[List[IConstraint], Dict[str, Fraction], Dict[str, Fraction]]:
        constraints = self.filter_constraints([c.constraint for c in cands])
        logger.info('@scaling_candidates ' + str(len(constraints)))
        if len(constraints) == 0:
            defaults: Dict[str, Fraction] = {}
            for box in self.example:
                for anchor in box.anchors:
                    defaults[str(anchor.id)] = to_frac(anchor.value)
            return ([], defaults, defaults)

        x_names: Dict[str, IConstraint] = {}
        y_names: Dict[str, IConstraint] = {}
        x_solver = z3.Optimize()
        y_solver = z3.Optimize()
        biases = self.build_biases(cands)
        if self.solve_unambig:
            biases = self.reward_parent_relative(biases)

        confs = conformance_range(self.min_conf, self.max_conf, scale=5)

        for constr_idx, constr in enumerate(constraints):
            cvname = "constr_var" + str(constr_idx)
            cvar = z3.Bool(cvname)
            if is_x_constr(constr):
                solver = x_solver; names_map = x_names
            else:
                solver = y_solver; names_map = y_names
            solver.add_soft(cvar, biases[constr])
            names_map[cvname] = constr

        for conf_idx, conf in enumerate(confs):
            self.add_conf_dims(x_solver, conf, conf_idx)
            self.add_conf_dims(y_solver, conf, conf_idx)
            self.add_layout_axioms(x_solver, conf_idx, self.targets, x_dim=True)
            self.add_layout_axioms(y_solver, conf_idx, self.targets, x_dim=False)
            for constr_idx, constr in enumerate(constraints):
                cvname = "constr_var" + str(constr_idx)
                cvar = z3.Bool(cvname)
                if is_x_constr(constr):
                    solver = x_solver
                else:
                    solver = y_solver
                solver.add(z3.Implies(cvar, constraint_to_z3_expr(constr, conf_idx)))

        if self.solve_unambig:
            if self.log_level != LogLevel.NONE: print('solving for unambiguous horizontal layout')
            x_cs, x_min, x_max = self.synth_unambiguous(x_solver, x_names, confs, x_dim=True, dry_run=False)
            if self.log_level != LogLevel.NONE: print('solving for unambiguous vertical layout')
            y_cs, y_min, y_max = self.synth_unambiguous(y_solver, y_names, confs, x_dim=False, dry_run=False)
        else:
            if self.log_level != LogLevel.NONE: print('solving for horizontal layout')
            x_cs, x_min, x_max = self.synth_unambiguous(x_solver, x_names, confs, x_dim=True, dry_run=True)
            if self.log_level != LogLevel.NONE: print('solving for vertical layout')
            y_cs, y_min, y_max = self.synth_unambiguous(y_solver, y_names, confs, x_dim=False, dry_run=True)

        return (x_cs + y_cs, dict(x_min, **y_min), dict(x_max, **y_max))


# Placeholder for blackbox pruner

