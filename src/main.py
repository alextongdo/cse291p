import kiwisolver

from src.logging import get_logger, setup_logging
from src.instantiation import ConditionalTemplateInstantiator, TemplateInstantiator
from src.learning import BayesianLearning, ConditionalBayesianLearning
from src.pruning import ConditionalHierarchicalPruner, HierarchicalPruner
from src.types import LinearConstraint, View

setup_logging(debug=True)


logger = get_logger(__name__)


def _add_layout_axioms(
    solver: kiwisolver.Solver,
    views: list[View],
    var_map: dict[str, kiwisolver.Variable],
):
    """
    Add fundamental layout axioms:
    - width = right - left
    - height = bottom - top
    - center_x = (left + right) / 2
    - center_y = (top + bottom) / 2
    - Non-negative constraints
    - Upper bounds to prevent unbounded solutions
    """
    for view in views:
        # Get variables
        width = var_map[f"{view.name}.width"]
        height = var_map[f"{view.name}.height"]
        left = var_map[f"{view.name}.left"]
        right = var_map[f"{view.name}.right"]
        top = var_map[f"{view.name}.top"]
        bottom = var_map[f"{view.name}.bottom"]
        center_x = var_map[f"{view.name}.center_x"]
        center_y = var_map[f"{view.name}.center_y"]

        # Add axioms (required strength)
        solver.addConstraint((width == right - left) | "required")
        solver.addConstraint((height == bottom - top) | "required")
        solver.addConstraint((center_x == (left + right) / 2) | "required")
        solver.addConstraint((center_y == (top + bottom) / 2) | "required")

        # Non-negative constraints
        solver.addConstraint((width >= 0) | "required")
        solver.addConstraint((height >= 0) | "required")
        solver.addConstraint((left >= 0) | "required")
        solver.addConstraint((top >= 0) | "required")

        # Upper bounds (weak) to prevent unbounded solutions
        for var in [left, right, top, bottom, width, height, center_x, center_y]:
            solver.addConstraint((var <= 10000.0) | "weak")


def _constraint_to_kiwi(
    constraint: LinearConstraint, var_map: dict[str, kiwisolver.Variable]
) -> kiwisolver.Constraint:
    """Convert a LinearConstraint to a Kiwi constraint."""
    y_var = var_map[f"{constraint.y.view.name}.{constraint.y.type}"]

    if constraint.x is None:
        # Constant constraint: y = b
        return (y_var == float(constraint.b)) | "required"
    else:
        # Linear constraint: y = a * x + b
        x_var = var_map[f"{constraint.x.view.name}.{constraint.x.type}"]

        # Kiwi only supports floats (unlike z3 which handles Fractions natively)
        a_val = float(constraint.a)
        b_val = float(constraint.b)

        return (y_var == a_val * x_var + b_val) | "required"


def _solve_layout(
    root: View, constraints: list[LinearConstraint], width: float, height: float
) -> dict[str, float]:
    """
    Solve constraints for a specific screen size.

    Args:
        root: Root view of the hierarchy
        constraints: List of synthesized constraints
        width: Desired screen width
        height: Desired screen height

    Returns:
        Dictionary mapping "view.anchor" to solved value
    """
    solver = kiwisolver.Solver()

    # Create variables for all anchors in the hierarchy
    var_map: dict[str, kiwisolver.Variable] = {}
    for view in root._flattened_views_in_subtree:
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
            key = f"{view.name}.{anchor_type}"
            var_map[key] = kiwisolver.Variable(key)

    # Add layout axioms
    _add_layout_axioms(solver, root._flattened_views_in_subtree, var_map)

    # Add synthesized constraints, skipping any that make the system infeasible
    for constraint in constraints:
        try:
            solver.addConstraint(_constraint_to_kiwi(constraint, var_map))
        except (
            kiwisolver.UnsatisfiableConstraint,
            kiwisolver.DuplicateConstraint,
        ):
            logger.warning(
                f"UNSAT constraint during layout solving: {repr(constraint)}"
            )

    # Fix root dimensions to desired size
    solver.addConstraint((var_map[f"{root.name}.width"] == width) | "required")
    solver.addConstraint((var_map[f"{root.name}.height"] == height) | "required")
    solver.addConstraint((var_map[f"{root.name}.left"] == 0) | "required")
    solver.addConstraint((var_map[f"{root.name}.top"] == 0) | "required")

    # Solve
    solver.updateVariables()

    # Debug: Print solved values
    logger.debug(f"Solved layout for width={width}, height={height}:")
    for view in root._flattened_views_in_subtree:
        vleft = var_map[f"{view.name}.left"].value()
        vtop = var_map[f"{view.name}.top"].value()
        vwidth = var_map[f"{view.name}.width"].value()
        vheight = var_map[f"{view.name}.height"].value()
        logger.debug(
            (
                f"  {view.name}: left={vleft:.2f}, top={vtop:.2f}, "
                f"width={vwidth:.2f}, height={vheight:.2f}"
            )
        )

    return {key: var.value() for key, var in var_map.items()}


class Mockdown:

    def fit(self, examples: list[View]) -> None:
        templates = TemplateInstantiator(examples).instantiate()
        candidates = BayesianLearning(examples=examples, seed=42).learn(templates)
        selected = HierarchicalPruner(examples).prune(candidates)
        self.constraints = selected
        # We need a copy of the root structure for prediction
        self.root = examples[0]

    def predict(
        self, width: int, height: int
    ) -> dict[str, tuple[float, float, float, float]]:
        """
        Use Kiwi solver to solve for a layout at the given width and height.

        Returns:
            Dictionary mapping view name to rect tuple (left, top, right, bottom)
        """
        solved_values = _solve_layout(self.root, self.constraints, width, height)

        # Convert solved anchor values to rect tuples per view
        result: dict[str, tuple[float, float, float, float]] = {}
        for view in self.root._flattened_views_in_subtree:
            left = solved_values[f"{view.name}.left"]
            top = solved_values[f"{view.name}.top"]
            right = solved_values[f"{view.name}.right"]
            bottom = solved_values[f"{view.name}.bottom"]
            result[view.name] = (left, top, right, bottom)

        return result


class ConditionalMockdown:

    def fit(self, examples: list[View]) -> None:
        example_idxs_to_templates_map = ConditionalTemplateInstantiator(
            examples=examples
        ).instantiate()
        example_idxs_to_constrs_map = ConditionalBayesianLearning(
            examples=examples, seed=42
        ).learn(example_idxs_to_templates_map)
        ex_to_selected_map = ConditionalHierarchicalPruner(examples=examples).prune(
            example_idxs_to_constrs_map
        )
        self.examples = examples
        self.ex_to_constrs_map = ex_to_selected_map

    def predict(
        self, width: int, height: int
    ) -> dict[str, tuple[float, float, float, float]]:
        # Should use kiwi solver to solver for a layout for the unseen width + height
        # Conditional will need to finding the closest example root size to the width + height
        pass
