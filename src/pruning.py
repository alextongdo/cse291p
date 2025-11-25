from fractions import Fraction

import z3
from pydantic import BaseModel

from src.types import Anchor, LinearConstraint, View


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
    # Calculate differences
    diff_w = Fraction(larger.width - smaller.width, num)
    diff_h = Fraction(larger.height - smaller.height, num)
    diff_l = Fraction(larger.left - smaller.left, num)
    diff_t = Fraction(larger.top - smaller.top, num)

    # If all diffs are zero, just return the smaller bound
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
    """Convert a LinearConstraint to a Z3 expression."""
    y_var = anchor_to_z3_var(constraint.y, test_rect_idx)

    if constraint.x is None:
        # Constant constraint: y = b
        return y_var == float(constraint.b)
    else:
        # Linear constraint: y = a * x + b
        x_var = anchor_to_z3_var(constraint.x, test_rect_idx)
        return y_var == float(constraint.a) * x_var + float(constraint.b)


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
            z3_weight = anchor_to_z3_var(view.anchor("width"), test_rect_idx)
            z3_left = anchor_to_z3_var(view.anchor("left"), test_rect_idx)
            z3_right = anchor_to_z3_var(view.anchor("right"), test_rect_idx)
            z3_center_x = anchor_to_z3_var(view.anchor("center_x"), test_rect_idx)

            solver.add(z3_weight == z3_right - z3_left)
            solver.add(z3_center_x == (z3_left + z3_right) / 2)
            solver.add(z3_weight >= 0, z3_left >= 0, z3_right >= 0)
        else:
            # Vertical axioms
            z3_height = anchor_to_z3_var(view.anchor("height"), test_rect_idx)
            z3_top = anchor_to_z3_var(view.anchor("top"), test_rect_idx)
            z3_bottom = anchor_to_z3_var(view.anchor("bottom"), test_rect_idx)
            z3_center_y = anchor_to_z3_var(view.anchor("center_y"), test_rect_idx)

            solver.add(z3_height == z3_bottom - z3_top)
            solver.add(z3_center_y == (z3_top + z3_bottom) / 2)
            solver.add(z3_height >= 0, z3_top >= 0, z3_bottom >= 0)


def add_root_dims_constraints(
    solver: z3.Optimize,
    test_rect: TestRect,
    test_rect_idx: int,
    root: View,
    is_horizontal: bool,
):
    """
    Add z3 constraints that the root view must be the same size as the text rect.
    """
    if is_horizontal:
        z3_width = anchor_to_z3_var(root.anchor("width"), test_rect_idx)
        z3_left = anchor_to_z3_var(root.anchor("left"), test_rect_idx)
        solver.add(z3_width == float(test_rect.width))
        solver.add(z3_left == float(test_rect.left))
    else:
        z3_height = anchor_to_z3_var(root.anchor("height"), test_rect_idx)
        z3_top = anchor_to_z3_var(root.anchor("top"), test_rect_idx)
        solver.add(z3_height == float(test_rect.height))
        solver.add(z3_top == float(test_rect.top))


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

    def __call__(
        self, candidates: list[LinearConstraint]
    ) -> tuple[list[LinearConstraint], dict[str, Fraction], dict[str, Fraction]]:
        """
        Solve MaxSMT for the given candidates.

        Args:
            candidates: List of constraints with scores

        Returns:
            selected_constraints: Chosen constraints
            mins: Dict mapping "view.anchor" -> min value
            maxes: Dict mapping "view.anchor" -> max value
        """

        for c in candidates:
            assert c.a is not None and c.b is not None
            assert c.score is not None

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

        if len(constraints) == 0:
            raise ValueError("No constraints were given to the MaxSMT pruner.")

        constraint_to_weight_map = get_constraint_weights(constraints)

        # Create test rect range
        test_rects = test_rect_range(self.min_rect, self.max_rect, num=5)

        # Solve horizontal and vertical constraints independently
        z3_vars_to_h_constr_map: dict[str, LinearConstraint] = {}
        z3_vars_to_v_constr_map: dict[str, LinearConstraint] = {}
        h_solver = z3.Optimize()
        v_solver = z3.Optimize()

        # Add constraint variables as soft constraints
        for constr_idx, constraint in enumerate(constraints):
            z3_name = f"constraint_{constr_idx}"  # boolean switch
            z3_var = z3.Bool(z3_name)

            if constraint.y.is_horizontal():
                solver = h_solver
                z3_vars_to_constr_map = z3_vars_to_h_constr_map
            else:
                solver = v_solver
                z3_vars_to_constr_map = z3_vars_to_v_constr_map

            # Scale to integer for Z3
            weight = int(constraint_to_weight_map[constraint] * 1000)
            solver.add_soft(z3_var, weight)
            z3_vars_to_constr_map[z3_name] = constraint

        # Add hard constraints for each conformance
        for test_rect_idx, test_rect in enumerate(test_rects):

            add_root_dims_constraints(
                h_solver, test_rect, test_rect_idx, self.root, is_horizontal=True
            )
            add_root_dims_constraints(
                v_solver, test_rect, test_rect_idx, self.root, is_horizontal=False
            )

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
            if v.name() in z3_vars_to_constr_map and z3.is_true(model[v])
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
                min_val = model.eval(min_var, model_completion=True)

                # Get anchor position under largest test rect (last index)
                max_idx = len(test_rects) - 1
                max_var = anchor_to_z3_var(view.anchor(anchor_type), max_idx)
                max_val = model.eval(max_var, model_completion=True)

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

    def __init__(self, examples: list[View]):
        """
        Initialize the hierarchical pruner.

        Args:
            examples: List of example layout instances
        """
        assert len(examples) > 0, "Pruner requires non-empty learning examples"

        self.examples = examples
        self.root = examples[0]

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

    def __call__(self, candidates: list[LinearConstraint]) -> list[LinearConstraint]:
        # Worklist: (focus_view, min_rect, max_rect)
        worklist = [(self.root, self.min_rect, self.max_rect)]
        output_constraints = set()

        while worklist:
            focus, min_rect, max_rect = worklist.pop()

            # Filter to relevant constraints for this level
            relevant = [c for c in candidates if self._is_relevant(focus, c)]

            if not relevant:
                continue

            max_smt_solver = MaxSMTPruner(focus, min_rect, max_rect)
            constraints, anchor_to_min_size_map, anchor_to_max_size_map = (
                max_smt_solver(relevant)
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

    def _is_relevant(self, focus: View, constraint: LinearConstraint) -> bool:
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
