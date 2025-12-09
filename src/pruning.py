import logging
from fractions import Fraction

import z3
from pydantic import BaseModel

from src.types import Anchor, LinearConstraint, View

logger = logging.getLogger(__name__)


class TestRect(BaseModel):
    """
    Represents a single test size/rect out of a range which constraints must satisfy
    to not be pruned. Stored as (l, t, w, h) instead of (l, t, r, b) for convenience.
    """

    left: Fraction
    top: Fraction
    width: Fraction
    height: Fraction


def test_rect_range(
    smaller: TestRect, larger: TestRect, num: int = 5
) -> list[TestRect]:
    """Generate evenly-spaced test rects between a smaller and larger rect."""
    diff_w = Fraction(larger.width - smaller.width, num)
    diff_h = Fraction(larger.height - smaller.height, num)
    diff_l = Fraction(larger.left - smaller.left, num)
    diff_t = Fraction(larger.top - smaller.top, num)

    if diff_w == 0 and diff_h == 0 and diff_l == 0 and diff_t == 0:
        return [smaller]

    rect_range = [smaller]
    for step in range(1, num - 1):
        rect_range.append(
            TestRect(
                left=smaller.left + diff_l * step,
                top=smaller.top + diff_t * step,
                width=smaller.width + diff_w * step,
                height=smaller.height + diff_h * step,
            )
        )
    rect_range.append(larger)
    return rect_range


def anchor_to_z3_var(anchor: Anchor, test_rect_idx: int) -> z3.ArithRef:
    """Create Z3 variable for an anchor under some test rect."""
    return z3.Real(f"{anchor.view.name}.{anchor.type}_{test_rect_idx}")


def constraint_to_z3_expr(
    constraint: LinearConstraint, test_rect_idx: int
) -> z3.BoolRef:
    """Convert a LinearConstraint to a Z3 expression.

    Note: We pass Fraction objects directly to Z3 (not floats) to preserve
    exact rational arithmetic. Z3 handles Python Fractions natively.
    """
    y_var = anchor_to_z3_var(constraint.y, test_rect_idx)

    if constraint.x is None:
        # Constant constraint: y = b
        return y_var == constraint.b
    else:
        # Linear constraint: y = a * x + b
        x_var = anchor_to_z3_var(constraint.x, test_rect_idx)
        return y_var == constraint.a * x_var + constraint.b


def add_layout_axioms(
    solver: z3.Optimize, views: list[View], test_rect_idx: int, is_horizontal: bool
):
    """
    Add horizontal or vertical layout axioms for a
    specific test rect, e.g. height = bottom - top.
    """
    for view in views:
        if is_horizontal:
            # Horizontal axioms
            z3_width = anchor_to_z3_var(view.anchor("width"), test_rect_idx)
            z3_left = anchor_to_z3_var(view.anchor("left"), test_rect_idx)
            z3_right = anchor_to_z3_var(view.anchor("right"), test_rect_idx)
            z3_center_x = anchor_to_z3_var(view.anchor("center_x"), test_rect_idx)

            solver.add(z3_width == z3_right - z3_left)
            solver.add(z3_center_x == (z3_left + z3_right) / 2)
            solver.add(z3_width >= 0)
            solver.add(z3_left >= 0)
            solver.add(z3_right >= 0)
            solver.add(z3_center_x >= 0)
        else:
            # Vertical axioms
            z3_height = anchor_to_z3_var(view.anchor("height"), test_rect_idx)
            z3_top = anchor_to_z3_var(view.anchor("top"), test_rect_idx)
            z3_bottom = anchor_to_z3_var(view.anchor("bottom"), test_rect_idx)
            z3_center_y = anchor_to_z3_var(view.anchor("center_y"), test_rect_idx)

            solver.add(z3_height == z3_bottom - z3_top)
            solver.add(z3_center_y == (z3_top + z3_bottom) / 2)
            solver.add(z3_height >= 0)
            solver.add(z3_top >= 0)
            solver.add(z3_bottom >= 0)
            solver.add(z3_center_y >= 0)


def add_root_dims_constraints(
    solver: z3.Optimize,
    test_rect: TestRect,
    test_rect_idx: int,
    root: View,
):
    """
    Add z3 constraints that the root view must be the same size as the test rect.

    Note: We pass Fraction objects directly to Z3 (not floats) to preserve exact rational arithmetic.
    """
    z3_width = anchor_to_z3_var(root.anchor("width"), test_rect_idx)
    z3_height = anchor_to_z3_var(root.anchor("height"), test_rect_idx)
    z3_left = anchor_to_z3_var(root.anchor("left"), test_rect_idx)
    z3_top = anchor_to_z3_var(root.anchor("top"), test_rect_idx)

    solver.add(z3_width == test_rect.width)
    solver.add(z3_height == test_rect.height)
    solver.add(z3_left == test_rect.left)
    solver.add(z3_top == test_rect.top)


def z3_to_fraction(z3_val) -> Fraction:
    """Convert Z3 numeric value to Fraction."""
    if hasattr(z3_val, "as_fraction"):
        return z3_val.as_fraction()
    else:
        # Handle integer/real values
        return Fraction(str(z3_val))


def get_constraint_weights(
    candidates: list[LinearConstraint],
) -> dict[LinearConstraint, float]:
    """
    Computes weights from constraint scores.
    Normalizes scores by minimum score to avoid numerical issues in Z3.
    """
    tiny = 0.000000001
    scores = {c: max(tiny, c.score) for c in candidates}
    min_score = min(scores.values())
    return {c: score / min_score + tiny for c, score in scores.items()}


class MaxSMTPruner:
    """Implements MaxSMT solver for constraint pruning."""

    def __init__(
        self,
        root: View,
        min_rect: TestRect,
        max_rect: TestRect,
    ):
        self.root = root
        self.root_and_children = [root] + root.children
        self.min_rect = min_rect
        self.max_rect = max_rect

    def prune(
        self,
        candidates: list[LinearConstraint],
        fixed_constraints: list[LinearConstraint] | None = None,
    ) -> tuple[list[LinearConstraint], dict[str, Fraction], dict[str, Fraction]]:
        """
        Solve MaxSMT for the given candidates using lexicographic optimization.

        Args:
            candidates: List of constraints with scores (soft, lower priority "p1")
            fixed_constraints: Optional list of constraints from supersets (soft, 
                higher priority "p0"). These are strongly preferred but can be 
                dropped if unsatisfiable for this group's test rect range.

        Returns:
            selected_constraints: Chosen constraints (from candidates only)
            mins: Dict mapping "view.anchor" -> min value
            maxes: Dict mapping "view.anchor" -> max value
        
        Note:
            Uses Z3's lexicographic optimization: first maximize "p0" (fixed/global),
            then subject to that, maximize "p1" (candidates/conditional).
        """
        if fixed_constraints is None:
            fixed_constraints = []

        for c in candidates:
            assert c.a is not None and c.b is not None
            assert c.score is not None

        for c in fixed_constraints:
            assert c.a is not None and c.b is not None

        # Filter constraints (following Mockdown's filter_constraints)
        # 1. Remove aspect ratio constraints (width = a * height)
        # 2. Keep only equality constraints
        def is_aspect_ratio(c: LinearConstraint) -> bool:
            """Check if constraint is an aspect ratio (width vs height of same view)."""
            if c.x is None:
                return False
            # Aspect ratio: same view, one is width and other is height
            return c.x.view.name == c.y.view.name and {c.x.type, c.y.type} == {
                "width",
                "height",
            }

        constraints = [c for c in candidates if not is_aspect_ratio(c)]
        filtered_fixed = [c for c in fixed_constraints if not is_aspect_ratio(c)]

        if len(constraints) == 0 and len(filtered_fixed) == 0:
            defaults: dict[str, Fraction] = {}
            for view in self.root_and_children:
                for anchor in view.anchors():
                    defaults[f"{view.name}.{anchor.type}"] = Fraction(
                        getattr(view, anchor.type)
                    )
            return ([], defaults, defaults)

        constraint_to_weight_map = get_constraint_weights(candidates) if candidates else {}

        # Create test rect range
        test_rects = test_rect_range(self.min_rect, self.max_rect, num=5)

        # Solve horizontal and vertical constraints independently
        z3_vars_to_h_constr_map: dict[str, LinearConstraint] = {}
        z3_vars_to_v_constr_map: dict[str, LinearConstraint] = {}
        h_solver = z3.Optimize()
        v_solver = z3.Optimize()

        # Add fixed constraints as HIGH PRIORITY soft constraints (group "p0")
        # These are from supersets (e.g., global) - strongly preferred but droppable
        for fixed_idx, fixed_constraint in enumerate(filtered_fixed):
            z3_name = f"fixed_{fixed_idx}"
            z3_var = z3.Bool(z3_name)

            if fixed_constraint.y.is_horizontal():
                solver = h_solver
            else:
                solver = v_solver

            # Use score if available, otherwise default weight of 1.0
            weight = fixed_constraint.score if fixed_constraint.score is not None else 1.0
            # Priority group "p0" - highest priority (optimized first)
            solver.add_soft(z3_var, weight, "p0")

        # Add candidate constraints as LOWER PRIORITY soft constraints (group "p1")
        for constr_idx, constraint in enumerate(constraints):
            z3_name = f"constraint_{constr_idx}"
            z3_var = z3.Bool(z3_name)

            if constraint.y.is_horizontal():
                solver = h_solver
                z3_vars_to_constr_map = z3_vars_to_h_constr_map
            else:
                solver = v_solver
                z3_vars_to_constr_map = z3_vars_to_v_constr_map

            weight = constraint_to_weight_map[constraint]
            # Priority group "p1" - lower priority (optimized after p0)
            solver.add_soft(z3_var, weight, "p1")
            z3_vars_to_constr_map[z3_name] = constraint

        # Add implications for each conformance (test rect)
        for test_rect_idx, test_rect in enumerate(test_rects):

            # Fixed constraints: if switch is true, constraint must hold
            for fixed_idx, fixed_constraint in enumerate(filtered_fixed):
                z3_name = f"fixed_{fixed_idx}"
                z3_var = z3.Bool(z3_name)
                expr = constraint_to_z3_expr(fixed_constraint, test_rect_idx)
                if fixed_constraint.y.is_horizontal():
                    h_solver.add(z3.Implies(z3_var, expr))
                else:
                    v_solver.add(z3.Implies(z3_var, expr))

            add_root_dims_constraints(h_solver, test_rect, test_rect_idx, self.root)
            add_root_dims_constraints(v_solver, test_rect, test_rect_idx, self.root)

            add_layout_axioms(
                h_solver, self.root_and_children, test_rect_idx, is_horizontal=True
            )
            add_layout_axioms(
                v_solver, self.root_and_children, test_rect_idx, is_horizontal=False
            )

            # If constraint selected, it must hold for this conformance
            for constr_idx, constraint in enumerate(constraints):
                z3_name = f"constraint_{constr_idx}"
                z3_var = z3.Bool(z3_name)
                expr = constraint_to_z3_expr(constraint, test_rect_idx)

                if constraint.y.is_horizontal():
                    h_solver.add(z3.Implies(z3_var, expr))
                else:
                    v_solver.add(z3.Implies(z3_var, expr))

        # Solve MaxSMT for both dimensions
        x_cs, x_min, x_max = self._solve_dimension(
            h_solver, z3_vars_to_h_constr_map, test_rects, is_horizontal=True
        )
        y_cs, y_min, y_max = self._solve_dimension(
            v_solver, z3_vars_to_v_constr_map, test_rects, is_horizontal=False
        )

        return (x_cs + y_cs, {**x_min, **y_min}, {**x_max, **y_max})

    def _solve_dimension(
        self,
        solver: z3.Optimize,
        z3_vars_to_constr_map: dict[str, LinearConstraint],
        test_rects: list[TestRect],
        is_horizontal: bool,
    ) -> tuple[list[LinearConstraint], dict[str, Fraction], dict[str, Fraction]]:
        """
        Solve one dimension and extract selected constraints + anchor bounds.

        Returns:
            selected_constraints: Chosen constraints
            mins: Dict mapping "view.anchor" -> min value
            maxes: Dict mapping "view.anchor" -> max value
        """
        # Solve MaxSMT
        if solver.check() != z3.sat:
            raise RuntimeError(
                "MaxSMT pruner could not solve for "
                f"{'horizontal' if is_horizontal else 'vertical'} dimension"
            )

        model = solver.model()

        # Extract selected constraints
        selected = [
            z3_vars_to_constr_map[v.name()]
            for v in model.decls()
            if v.name() in z3_vars_to_constr_map and model.get_interp(v)
        ]

        # Extract anchor position at smallest and largest test rects
        mins: dict[str, Fraction] = {}
        maxes: dict[str, Fraction] = {}

        anchor_types = (
            ["width", "left", "right", "center_x"]
            if is_horizontal
            else ["height", "top", "bottom", "center_y"]
        )

        for view in self.root_and_children:
            for anchor_type in anchor_types:
                # Get anchor position under smallest test rect (index 0)
                min_var = anchor_to_z3_var(view.anchor(anchor_type), 0)
                min_val = model.get_interp(min_var)

                # Get anchor position under largest test rect (last index)
                max_idx = len(test_rects) - 1
                max_var = anchor_to_z3_var(view.anchor(anchor_type), max_idx)
                max_val = model.get_interp(max_var)

                key = f"{view.name}.{anchor_type}"
                mins[key] = z3_to_fraction(min_val)
                maxes[key] = z3_to_fraction(max_val)

        return (selected, mins, maxes)


class HierarchicalPruner:
    """
    Hierarchical constraint pruner using level-by-level decomposition.

    The key innovation: solve each level of the view hierarchy independently
    using BlackBoxPruner, then infer child bounds from parent solutions.
    """

    def __init__(
        self,
        examples: list[View],
        min_rect: TestRect | None = None,
        max_rect: TestRect | None = None,
    ):
        """
        Initialize the hierarchical pruner.

        Args:
            examples: List of example layout instances
            min_rect: Optional minimum test rect (if None, computed from examples)
            max_rect: Optional maximum test rect (if None, computed from examples)
        """
        assert len(examples) > 0, "Pruner requires non-empty learning examples"

        self.examples = examples
        self.root = examples[0]

        if min_rect is not None and max_rect is not None:
            self.min_rect = min_rect
            self.max_rect = max_rect
        else:
            widths = [Fraction(ex.width) for ex in examples]
            heights = [Fraction(ex.height) for ex in examples]
            lefts = [Fraction(ex.left) for ex in examples]
            tops = [Fraction(ex.top) for ex in examples]

            self.min_rect = TestRect(
                left=min(lefts), top=min(tops), width=min(widths), height=min(heights)
            )
            self.max_rect = TestRect(
                left=max(lefts), top=max(tops), width=max(widths), height=max(heights)
            )

    def prune(
        self,
        candidates: list[LinearConstraint],
        fixed_constraints: list[LinearConstraint] | None = None,
    ) -> list[LinearConstraint]:
        """
        Prune candidates hierarchically.

        Args:
            candidates: Constraints to prune (soft, can be dropped)
            fixed_constraints: Optional constraints that must be satisfied (hard)
        """
        if fixed_constraints is None:
            fixed_constraints = []

        # Worklist: (focus_view, min_rect, max_rect)
        worklist = [(self.root, self.min_rect, self.max_rect)]
        output_constraints = set()

        while worklist:
            focus, min_rect, max_rect = worklist.pop()

            # Filter to relevant constraints for this level
            relevant = [
                c for c in candidates if HierarchicalPruner._is_relevant(focus, c)
            ]
            relevant_fixed = [
                c for c in fixed_constraints if HierarchicalPruner._is_relevant(focus, c)
            ]

            max_smt_solver = MaxSMTPruner(focus, min_rect, max_rect)
            constraints, anchor_to_min_size_map, anchor_to_max_size_map = (
                max_smt_solver.prune(relevant, fixed_constraints=relevant_fixed)
            )
            output_constraints.update(constraints)

            # Add children to worklist with inferred bounds
            for child in focus.children:
                child_min_rect = TestRect(
                    width=anchor_to_min_size_map[f"{child.name}.width"],
                    height=anchor_to_min_size_map[f"{child.name}.height"],
                    left=anchor_to_min_size_map[f"{child.name}.left"],
                    top=anchor_to_min_size_map[f"{child.name}.top"],
                )
                child_max_rect = TestRect(
                    width=anchor_to_max_size_map[f"{child.name}.width"],
                    height=anchor_to_max_size_map[f"{child.name}.height"],
                    left=anchor_to_max_size_map[f"{child.name}.left"],
                    top=anchor_to_max_size_map[f"{child.name}.top"],
                )

                worklist.append((child, child_min_rect, child_max_rect))

        return list(output_constraints)

    @staticmethod
    def _is_relevant(focus: View, constraint: LinearConstraint) -> bool:
        """
        Check if constraint contains anchors that are children of the focused view or
        the focused view itself. For constant constraints, the anchor must be a child
        of the focused view.
        """
        if constraint.x is not None:
            # Linear constraint: y and x must be siblings or parent-child
            y_anchor_view_name = constraint.y.view.name
            x_anchor_view_name = constraint.x.view.name
            child_view_names = {child.name for child in focus.children}
            child_or_parent_names = child_view_names | {focus.name}
            return (
                x_anchor_view_name in child_or_parent_names
                and y_anchor_view_name in child_or_parent_names
                and x_anchor_view_name != y_anchor_view_name
            )
        else:
            # Constant constraint: y must be a child
            y_anchor_view_name = constraint.y.view.name
            return any(child.name == y_anchor_view_name for child in focus.children)


class ConditionalHierarchicalPruner:
    """
    Hierarchical pruning for conditional constraints with overlapping groups.

    Handles cases where groups overlap (e.g., constraints in (0,1) must be
    compatible with constraints in (0,) when applied to example 0).

    Uses width-based midpoint breakpoints to define the test range for each
    example, ensuring constraints generalize within their applicable range.
    """

    def __init__(self, examples: list[View]):
        self.examples = examples

    def prune(
        self,
        conditional_constraints: dict[tuple[int, ...], list[LinearConstraint]],
    ) -> dict[tuple[int, ...], list[LinearConstraint]]:
        """
        Per-group pruning for conditional constraints with global as fixed context.

        Algorithm:
        1. First, prune global constraints (all examples) using Original's algorithm
        2. For conditional groups, prune with global constraints as FIXED context
           - Global constraints are hard constraints that must be satisfied
           - Conditional constraints are soft (candidates that can be dropped)
           - Only conditional constraints compatible with global survive

        This ensures:
        - Global constraints behave exactly like Original
        - Conditional constraints are compatible with global (no runtime conflicts)
        - No runtime conflict resolution needed at prediction time

        Args:
            conditional_constraints: Dict mapping example index tuples to constraints
                e.g., {(0,): [...], (0, 1): [...], (0, 1, 2): [...]}

        Returns:
            Dict with same structure, constraints pruned per group
        """
        n = len(self.examples)
        global_key = tuple(range(n))
        output: dict[tuple[int, ...], list[LinearConstraint]] = {}

        # Step 1: Prune global constraints using Original's algorithm
        global_constraints = conditional_constraints.get(global_key, [])
        if global_constraints:
            logger.info(
                f"  Pruning global group {global_key}: "
                f"{len(global_constraints)} constraints with {n} examples"
            )
            pruned_global = HierarchicalPruner(self.examples).prune(global_constraints)
            logger.info(f"    → {len(pruned_global)} constraints survived")
        else:
            pruned_global = []

        output[global_key] = pruned_global

        # Step 2: For conditional groups, prune WITH all supersets as fixed context
        # Sort by size (largest first, excluding global which is already done)
        # This ensures larger groups are pruned before smaller groups that are subsets
        conditional_groups = sorted(
            [k for k in conditional_constraints.keys() if k != global_key],
            key=lambda k: -len(k),
        )

        for group_key in conditional_groups:
            constraints = conditional_constraints[group_key]
            group_examples = [self.examples[i] for i in group_key]
            group_set = set(group_key)

            # Collect fixed constraints from ALL supersets (including global)
            # A superset's constraints will apply whenever this group's constraints apply
            fixed_constraints: list[LinearConstraint] = list(pruned_global)
            superset_keys = []

            for other_key, other_constraints in output.items():
                if other_key == global_key:
                    continue  # Already included
                # Check if this group is a strict subset of other_key
                if group_set < set(other_key):
                    fixed_constraints.extend(other_constraints)
                    superset_keys.append(other_key)

            logger.info(
                f"  Pruning conditional group {group_key}: "
                f"{len(constraints)} constraints with {len(group_examples)} examples "
                f"(+ {len(fixed_constraints)} fixed from global + {superset_keys})"
            )

            # Prune with all superset constraints as fixed (hard) context
            pruned = HierarchicalPruner(group_examples).prune(
                constraints, fixed_constraints=fixed_constraints
            )

            logger.info(f"    → {len(pruned)} constraints survived")
            output[group_key] = pruned

        return output
