"""
Hierarchical Constraint Pruning with MaxSMT

Based on Mockdown's hierarchical pruning algorithm. Selects optimal subset of
candidate constraints using Z3 MaxSMT solver with level-by-level decomposition.

Architecture:
- BlackBoxPruner: Low-level MaxSMT solver for a set of views
- HierarchicalPruner: High-level decomposition strategy using BlackBoxPruner
"""

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

import z3

from src.types import Anchor, LinearConstraint, View


@dataclass(frozen=True)
class Conformance:
    """A specific test size/position for layout validation."""

    width: Fraction
    height: Fraction
    x: Fraction
    y: Fraction


def conformance_range(
    lower: Conformance, upper: Conformance, scale: int = 5
) -> list[Conformance]:
    """
    Generate evenly-spaced conformances between lower and upper bounds.

    Args:
        lower: Minimum conformance
        upper: Maximum conformance
        scale: Number of steps (default: 5)

    Returns:
        List of conformances from lower to upper
    """
    # Calculate differences
    diff_w = Fraction(upper.width - lower.width, scale)
    diff_h = Fraction(upper.height - lower.height, scale)
    diff_x = Fraction(upper.x - lower.x, scale)
    diff_y = Fraction(upper.y - lower.y, scale)

    # If all diffs are zero, just return the lower bound
    if diff_w == 0 and diff_h == 0 and diff_x == 0 and diff_y == 0:
        return [lower]

    # Build intermediate conformances
    def builder(step: int) -> Conformance:
        return Conformance(
            lower.width + diff_w * step,
            lower.height + diff_h * step,
            lower.x + diff_x * step,
            lower.y + diff_y * step,
        )

    # Ensure the range is stable by manually adding upper and lower bounds
    return [lower] + [builder(step) for step in range(1, scale - 1)] + [upper]


def anchor_to_z3_var(anchor: Anchor, conf_idx: int) -> z3.ArithRef:
    """Create Z3 variable for an anchor at a specific conformance."""
    return z3.Real(f"{anchor.view.name}.{anchor.type}_{conf_idx}")


def constraint_to_z3_expr(constraint: LinearConstraint, conf_idx: int) -> z3.BoolRef:
    """
    Convert a LinearConstraint to a Z3 expression.

    Args:
        constraint: The constraint to convert
        conf_idx: The conformance index (suffix for Z3 variables)

    Returns:
        Z3 boolean expression representing the constraint
    """
    y_var = anchor_to_z3_var(constraint.y, conf_idx)

    if constraint.x is None:
        # Constant constraint: y = b
        return y_var == float(constraint.b)
    else:
        # Linear constraint: y = a * x + b
        x_var = anchor_to_z3_var(constraint.x, conf_idx)
        a_float = float(constraint.a) if constraint.a is not None else 1.0
        b_float = float(constraint.b) if constraint.b is not None else 0.0
        return y_var == a_float * x_var + b_float


def is_horizontal(constraint: LinearConstraint) -> bool:
    """Check if constraint is horizontal (x dimension)."""
    h_types = {"left", "right", "width", "center_x"}
    return constraint.y.type in h_types


def add_layout_axioms(
    solver: z3.Optimize, views: list[View], conf_idx: int, x_dim: bool
):
    """
    Add layout axioms for a specific conformance and dimension.

    Layout axioms enforce geometric relationships:
    - Horizontal: width = right - left, center_x = (left + right) / 2
    - Vertical: height = bottom - top, center_y = (top + bottom) / 2
    """
    for view in views:
        if x_dim:
            # Horizontal axioms
            w = anchor_to_z3_var(Anchor(view=view, type="width"), conf_idx)
            l = anchor_to_z3_var(Anchor(view=view, type="left"), conf_idx) # noqa: E741
            r = anchor_to_z3_var(Anchor(view=view, type="right"), conf_idx)
            cx = anchor_to_z3_var(Anchor(view=view, type="center_x"), conf_idx)

            solver.add(w == r - l)
            solver.add(cx == (l + r) / 2)
            solver.add(w >= 0, l >= 0, r >= 0)
        else:
            # Vertical axioms
            h = anchor_to_z3_var(Anchor(view=view, type="height"), conf_idx)
            t = anchor_to_z3_var(Anchor(view=view, type="top"), conf_idx)
            b = anchor_to_z3_var(Anchor(view=view, type="bottom"), conf_idx)
            cy = anchor_to_z3_var(Anchor(view=view, type="center_y"), conf_idx)

            solver.add(h == b - t)
            solver.add(cy == (t + b) / 2)
            solver.add(h >= 0, t >= 0, b >= 0)


def add_conformance_dims(
    solver: z3.Optimize, conf: Conformance, conf_idx: int, root: View, x_dim: bool
):
    """
    Fix root dimensions for a specific conformance.

    Args:
        solver: Z3 solver
        conf: Conformance to apply
        conf_idx: Conformance index
        root: Root view
        x_dim: True for horizontal, False for vertical
    """
    if x_dim:
        w = anchor_to_z3_var(Anchor(view=root, type="width"), conf_idx)
        l = anchor_to_z3_var(Anchor(view=root, type="left"), conf_idx) # noqa: E741
        solver.add(w == float(conf.width))
        solver.add(l == float(conf.x))
    else:
        h = anchor_to_z3_var(Anchor(view=root, type="height"), conf_idx)
        t = anchor_to_z3_var(Anchor(view=root, type="top"), conf_idx)
        solver.add(h == float(conf.height))
        solver.add(t == float(conf.y))


def to_fraction(z3_val) -> Fraction:
    """Convert Z3 numeric value to Fraction."""
    if hasattr(z3_val, "as_fraction"):
        return z3_val.as_fraction()
    else:
        # Handle integer/real values
        return Fraction(str(z3_val))


def build_biases(candidates: list[LinearConstraint]) -> dict[LinearConstraint, float]:
    """
    Build weight biases from constraint scores.

    Normalizes scores by minimum score to avoid numerical issues in Z3.
    Based on Mockdown's build_biases function.
    """
    tiny = 0.000000001
    scores = {
        c: max(tiny, c.score) if c.score is not None else tiny for c in candidates
    }
    min_score = min(scores.values())
    return {constr: score / min_score + tiny for constr, score in scores.items()}


class BlackBoxPruner:
    """
    Low-level MaxSMT solver for constraint pruning.

    Solves MaxSMT for a given set of target views, maximizing the sum of
    constraint scores subject to layout axioms.
    """

    def __init__(
        self,
        examples: Sequence[View],
        min_conf: Conformance,
        max_conf: Conformance,
        targets: Sequence[View] | None = None,
    ):
        """
        Initialize BlackBoxPruner.

        Args:
            examples: List of example layout instances
            min_conf: Minimum conformance bounds
            max_conf: Maximum conformance bounds
            targets: Views to solve for (default: all views in hierarchy)
        """
        assert len(examples) > 0, "Pruner requires non-empty learning examples"

        self.examples = examples
        self.root = examples[0]
        self.min_conf = min_conf
        self.max_conf = max_conf

        # Targets: views to optimize (default to entire hierarchy)
        if targets is not None:
            self.targets = list(targets)
        else:
            self.targets = self.root._flattened_views_in_subtree

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

        constraints = [
            c
            for c in candidates
            if not is_aspect_ratio(c) and (c.a is not None or c.b is not None)
        ]

        if len(constraints) == 0:
            # Return empty results with default anchor values
            defaults: dict[str, Fraction] = {}
            for view in self.targets:
                for anchor_type in [
                    "left",
                    "right",
                    "top",
                    "bottom",
                    "width",
                    "height",
                    "center_x",
                    "center_y",
                ]:
                    defaults[f"{view.name}.{anchor_type}"] = Fraction(
                        getattr(view, anchor_type)
                    )
            return ([], defaults, defaults)

        # Build biases (weights) from scores
        biases = build_biases(constraints)

        # Create conformance range
        confs = conformance_range(self.min_conf, self.max_conf, scale=5)

        # Separate constraints by dimension
        x_names: dict[str, LinearConstraint] = {}
        y_names: dict[str, LinearConstraint] = {}
        x_solver = z3.Optimize()
        y_solver = z3.Optimize()

        # Add constraint variables as soft constraints
        for constr_idx, constr in enumerate(constraints):
            cvname = f"constr_var{constr_idx}"
            cvar = z3.Bool(cvname)

            if is_horizontal(constr):
                solver = x_solver
                names_map = x_names
            else:
                solver = y_solver
                names_map = y_names

            # Add soft constraint with weight from bias
            weight = int(biases[constr] * 1000)  # Scale to integer for Z3
            solver.add_soft(cvar, weight)
            names_map[cvname] = constr

        # Add hard constraints for each conformance
        for conf_idx, conf in enumerate(confs):
            # Fix root dimensions
            add_conformance_dims(x_solver, conf, conf_idx, self.root, x_dim=True)
            add_conformance_dims(y_solver, conf, conf_idx, self.root, x_dim=False)

            # Add layout axioms for all targets
            add_layout_axioms(x_solver, self.targets, conf_idx, x_dim=True)
            add_layout_axioms(y_solver, self.targets, conf_idx, x_dim=False)

            # If constraint selected, it must hold for this conformance
            for constr_idx, constr in enumerate(constraints):
                cvname = f"constr_var{constr_idx}"
                cvar = z3.Bool(cvname)
                expr = constraint_to_z3_expr(constr, conf_idx)

                if is_horizontal(constr):
                    x_solver.add(z3.Implies(cvar, expr))
                else:
                    y_solver.add(z3.Implies(cvar, expr))

        # Solve MaxSMT for both dimensions
        x_cs, x_min, x_max = self._solve_dimension(x_solver, x_names, confs, x_dim=True)
        y_cs, y_min, y_max = self._solve_dimension(
            y_solver, y_names, confs, x_dim=False
        )

        return (x_cs + y_cs, {**x_min, **y_min}, {**x_max, **y_max})

    def _solve_dimension(
        self,
        solver: z3.Optimize,
        names_map: dict[str, LinearConstraint],
        confs: list[Conformance],
        x_dim: bool,
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
            print(f"WARNING: No solution found for {'x' if x_dim else 'y'} dimension")
            return ([], {}, {})

        model = solver.model()

        # Extract selected constraints
        selected = [
            names_map[v.name()]
            for v in model.decls()
            if v.name() in names_map and z3.is_true(model[v])
        ]

        # Extract anchor values at min (first) and max (last) conformances
        mins: dict[str, Fraction] = {}
        maxes: dict[str, Fraction] = {}

        anchor_types = (
            ["width", "left", "right", "center_x"]
            if x_dim
            else ["height", "top", "bottom", "center_y"]
        )

        for view in self.targets:
            for anchor_type in anchor_types:
                # Get value at min conformance (index 0)
                min_var = anchor_to_z3_var(Anchor(view=view, type=anchor_type), 0)
                min_val = model.eval(min_var, model_completion=True)

                # Get value at max conformance (last index)
                max_idx = len(confs) - 1
                max_var = anchor_to_z3_var(Anchor(view=view, type=anchor_type), max_idx)
                max_val = model.eval(max_var, model_completion=True)

                key = f"{view.name}.{anchor_type}"
                mins[key] = to_fraction(min_val)
                maxes[key] = to_fraction(max_val)

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

        # Compute initial bounds from examples
        widths = [Fraction(ex.width) for ex in examples]
        heights = [Fraction(ex.height) for ex in examples]
        xs = [Fraction(ex.left) for ex in examples]
        ys = [Fraction(ex.top) for ex in examples]

        self.min_conf = Conformance(min(widths), min(heights), min(xs), min(ys))
        self.max_conf = Conformance(max(widths), max(heights), max(xs), max(ys))

    def __call__(self, candidates: list[LinearConstraint]) -> list[LinearConstraint]:
        """
        Main entry point: prune candidates using hierarchical decomposition.

        Args:
            candidates: List of constraints with scores from Bayesian learning

        Returns:
            List of selected constraints
        """
        # Worklist: (focus_view, focus_examples, min_conf, max_conf)
        worklist = [(self.root, self.examples, self.min_conf, self.max_conf)]
        output_constraints = set()

        while worklist:
            focus, focus_examples, min_c, max_c = worklist.pop()

            # Filter to relevant constraints for this level
            relevant = [c for c in candidates if self._is_relevant(focus, c)]

            if not relevant:
                continue

            # Solve this level using BlackBoxPruner
            targets = [focus] + list(focus.children)
            bb_solver = BlackBoxPruner(focus_examples, min_c, max_c, targets=targets)
            focus_output, mins, maxes = bb_solver(relevant)

            output_constraints.update(focus_output)

            # Add children to worklist with inferred bounds
            for child in focus.children:
                # Build child conformances from mins/maxes
                def get_key(anchor_type: str) -> str:
                    return f"{child.name}.{anchor_type}" # noqa: B023

                child_min = Conformance(
                    width=mins[get_key("width")],
                    height=mins[get_key("height")],
                    x=mins[get_key("left")],
                    y=mins[get_key("top")],
                )
                child_max = Conformance(
                    width=maxes[get_key("width")],
                    height=maxes[get_key("height")],
                    x=maxes[get_key("left")],
                    y=maxes[get_key("top")],
                )

                # Find child examples
                child_examples = [
                    self._find_view_in_example(child.name, ex) for ex in focus_examples
                ]

                worklist.append((child, child_examples, child_min, child_max))

        return list(output_constraints)

    def _is_relevant(self, focus: View, constraint: LinearConstraint) -> bool:
        """
        Check if constraint is relevant to this parent-child level.

        A constraint is relevant if:
        - For linear constraints (y = a*x + b): either x or y is a child,
          and the other is focus or another child
        - For constant constraints (y = b): y is a child

        Based on Mockdown's relevant_constraint function.
        """
        if constraint.x is not None:
            # Linear constraint: check if x or y is a child
            y_name = constraint.y.view.name
            x_name = constraint.x.view.name

            for child in focus.children:
                if child.name == x_name:
                    # x is a child, y should be focus or another child
                    if focus.name == y_name:
                        return True
                    for sibling in focus.children:
                        if sibling.name == y_name:
                            return True
                elif child.name == y_name:
                    # y is a child, x should be focus or another child
                    if focus.name == x_name:
                        return True
                    for sibling in focus.children:
                        if sibling.name == x_name:
                            return True
            return False
        else:
            # Constant constraint: y should be a child
            y_name = constraint.y.view.name
            return any(child.name == y_name for child in focus.children)

    def _find_view_in_example(self, view_name: str, example: View) -> View:
        """Find a view by name in an example hierarchy."""
        for view in example._flattened_views_in_subtree:
            if view.name == view_name:
                return view
        raise ValueError(f"View {view_name} not found in example")
