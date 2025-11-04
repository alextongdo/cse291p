"""Hierarchical decomposition via HierarchicalPruner.

Reimplements:
- mockdown/src/mockdown/pruning/blackbox.py (HierarchicalPruner parts)
"""

from fractions import Fraction
from typing import Dict, List, Set, Tuple

import sympy as sym

from cse291p.pipeline.constraint import IConstraint, ConstraintKind
from cse291p.pipeline.constraint.constraint import ConstantConstraint
from cse291p.pipeline.view import IView, IAnchor
from cse291p.types import NT
from .conformance import Conformance, confs_to_bounds, to_rect, conf_zip
from .types import ISizeBounds, BasePruningMethod
from .blackbox import BlackBoxPruner, is_x_constr, LogLevel
from .util import short_str, to_frac


class HierarchicalPruner(BasePruningMethod):
    def __init__(self, examples: List[IView[NT]], bounds: ISizeBounds, solve_unambig: bool):
        bounds_frac = {k: to_frac(v) if v else None for k, v in bounds.items()}

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

        self.hierarchy = examples[0]
        self.examples = examples

        self.top_width = self.hierarchy.width_anchor
        self.top_height = self.hierarchy.height_anchor
        self.top_x = self.hierarchy.left_anchor
        self.top_y = self.hierarchy.top_anchor

        self.solve_unambig = solve_unambig
        self.log_level = LogLevel.NONE

    def relevant_constraint(self, focus: IView[NT], c: IConstraint) -> bool:
        if c.x_id:
            y_name = c.y_id.view_name
            x_name = c.x_id.view_name
            for child in focus.children:
                if child.name == x_name:
                    return focus.name == y_name or focus.is_parent_of_name(y_name)
                elif child.name == y_name:
                    return focus.name == x_name or focus.is_parent_of_name(x_name)
            return False
        else:
            for child in focus.children:
                if child.name == c.y_id.view_name:
                    return True
            return False

    def infer_child_confs(self, constrs: List[IConstraint], focus: IView[NT], min_c: Conformance, max_c: Conformance) -> \
            Dict[str, Dict[str, Conformance]]:
        from z3 import z3  # local import to avoid heavy import unless used
        all_boxes = [focus] + [child for child in focus.children]
        x_solver = z3.Optimize(); y_solver = z3.Optimize()
        z3_idx = 0
        self.add_layout_axioms(x_solver, z3_idx, all_boxes, x_dim=True)
        self.add_layout_axioms(y_solver, z3_idx, all_boxes, x_dim=False)
        output: Dict[str, Dict[str, Conformance]] = {}
        p_w, p_h = anchor_id_to_z3_var(focus.width_anchor.id, z3_idx), anchor_id_to_z3_var(focus.height_anchor.id, z3_idx)
        p_x, p_y = anchor_id_to_z3_var(focus.left_anchor.id, z3_idx), anchor_id_to_z3_var(focus.top_anchor.id, z3_idx)
        x_solver.add(p_w <= max_c.width); y_solver.add(p_h <= max_c.height)
        x_solver.add(p_x <= max_c.x); y_solver.add(p_y <= max_c.y)
        x_solver.add(p_w >= min_c.width); y_solver.add(p_h >= min_c.height)
        x_solver.add(p_x >= min_c.x); y_solver.add(p_y >= min_c.y)
        for constr in constrs:
            if is_x_constr(constr): x_solver.add(constraint_to_z3_expr(constr, z3_idx))
            else: y_solver.add(constraint_to_z3_expr(constr, z3_idx))
        for child in focus.children:
            c_w, c_h = anchor_id_to_z3_var(child.width_anchor.id, z3_idx), anchor_id_to_z3_var(child.height_anchor.id, z3_idx)
            c_x, c_y = anchor_id_to_z3_var(child.left_anchor.id, z3_idx), anchor_id_to_z3_var(child.top_anchor.id, z3_idx)
            max_vals: List[Fraction] = []; min_vals: List[Fraction] = []
            contexts = [(c_w, x_solver), (c_h, y_solver), (c_x, x_solver), (c_y, y_solver)]
            for var, solver in contexts:
                solver.push(); solver.maximize(var); chk = solver.check()
                if chk == z3.sat:
                    val: Fraction = solver.model().get_interp(var).as_fraction(); max_vals.append(val)
                else:
                    raise Exception('unsat child conformance in maximize')
                solver.pop(); solver.push(); solver.minimize(var); chk = solver.check()
                if chk == z3.sat:
                    val = solver.model().get_interp(var).as_fraction(); min_vals.append(val)
                else:
                    raise Exception('unsat child conformance in minimize')
                solver.pop()
            output[child.name] = {'max': Conformance(*max_vals), 'min': Conformance(*min_vals)}
        return output

    def confs_to_constrs(self, child: IView[NT], min_c: Conformance, max_c: Conformance) -> List[IConstraint]:
        kind = ConstraintKind.SIZE_CONSTANT
        out: List[IConstraint] = []
        for var, bound in conf_zip(min_c, child):
            out.append(ConstantConstraint(kind=kind, y_id=var.id, b=sym.Rational(bound), op=operator.ge))
        for var, bound in conf_zip(max_c, child):
            out.append(ConstantConstraint(kind=kind, y_id=var.id, b=sym.Rational(bound), op=operator.le))
        return out

    def integrate_constraints(self, examples: List[IView[NT]], min_c: Conformance, max_c: Conformance, constraints: List[IConstraint]) -> List[IConstraint]:
        result = BlackBoxPruner(examples, confs_to_bounds(min_c, max_c), self.solve_unambig)(constraints)[0]
        diff = set(constraints) - set(result)
        if len(diff) > 0:
            print('pruning during integration: ', [short_str(c) for c in diff])
        return result + [replace(constr, priority=PRIORITY_STRONG) for constr in diff]

    def validate_output_constrs(self, constraints: Set[ConstraintCandidate]) -> None:
        from z3 import z3
        from cse291p.pipeline.integration.kiwi import evaluate_constraints
        solver = z3.Optimize()
        bb_solver = BlackBoxPruner([self.hierarchy], confs_to_bounds(self.min_conf, self.max_conf), self.solve_unambig)
        baseline_set = set(bb_solver(list(constraints))[0])
        inconceivables = constraints - baseline_set
        if len(inconceivables) > 0:
            print('ERROR: black box found the following unsat core:')
            print([short_str(c.constraint) for c in inconceivables])
            evaluate_constraints(self.hierarchy, to_rect(self.min_conf), list(baseline_set))
            raise Exception('inconceivable')
        evaluate_constraints(self.hierarchy, to_rect(self.min_conf), list(constraints))
        return

    def __call__(self, cands: List[ConstraintCandidate]) -> Tuple[List[IConstraint], Dict[str, Fraction], Dict[str, Fraction]]:
        infer_with_z3 = True
        validate = False
        debug = True
        integrate = False

        worklist = []
        start = (self.hierarchy, self.examples, self.min_conf, self.max_conf)
        if debug: print('starting hierarchical pruning with ', start)
        worklist.append(start)
        output_constrs = set()

        while len(worklist) > 0:
            focus, focus_examples, min_c, max_c = worklist.pop()
            if self.log_level != LogLevel.NONE:
                print('solving for ', focus, 'with bounds ', min_c, max_c)
            relevant = [c for c in cands if self.relevant_constraint(focus, c.constraint)]
            targets = [focus] + [child for child in focus.children]
            bounds = confs_to_bounds(min_c, max_c)
            bb_solver = BlackBoxPruner(focus_examples, bounds, self.solve_unambig, targets=targets)
            bb_solver.log_level = self.log_level
            focus_output, mins, maxes = bb_solver(relevant)
            output_constrs |= set(focus_output)
            if integrate and len(focus_output) > 0:
                int_output_constrs = set(self.integrate_constraints(self.examples, self.min_conf, self.max_conf, list(output_constrs)))
                output_constrs = int_output_constrs
            if validate: self.validate_output_constrs(output_constrs)
            if not infer_with_z3:
                child_confs = self.infer_child_confs(list(output_constrs), focus, min_c, max_c)
            for ci, child in enumerate(focus.children):
                def get(anc: IAnchor[NT]) -> str:
                    return str(anc.id)
                if infer_with_z3:
                    clo = Conformance(mins[get(child.width_anchor)], mins[get(child.height_anchor)], mins[get(child.left_anchor)], mins[get(child.top_anchor)])
                    chi = Conformance(maxes[get(child.width_anchor)], maxes[get(child.height_anchor)], maxes[get(child.left_anchor)], maxes[get(child.top_anchor)])
                else:
                    clo, chi = child_confs[child.name]['min'], child_confs[child.name]['max']
                worklist.append((child, [fe.children[ci] for fe in focus_examples], clo, chi))
            with open('constraints.json', 'a') as debugout:
                print([short_str(c) for c in focus_output], file=debugout)

        print('done with hierarchical pruning! finishing up...')
        if integrate:
            output_constrs = set(self.integrate_constraints(self.examples, self.min_conf, self.max_conf, list(output_constrs)))
        if debug and validate:
            self.validate_output_constrs(output_constrs)
        if self.log_level != LogLevel.NONE:
            self.dump_constraints("output.smt2", self.hierarchy, list(output_constrs))
        return (list(output_constrs), {}, {})


# Placeholder for hierarchical pruner

