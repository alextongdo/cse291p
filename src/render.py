"""
Simple HTML renderer for synthesized layout constraints.
Uses Kiwi constraint solver to generate concrete layouts.
"""

import tempfile
import webbrowser
from fractions import Fraction

import kiwisolver
from jinja2 import Template

from src.types import Anchor, LinearConstraint, View


def anchor_to_kiwi_var(anchor: Anchor) -> kiwisolver.Variable:
    """Create a Kiwi variable for an anchor."""
    return kiwisolver.Variable(f"{anchor.view.name}.{anchor.type}")


def add_layout_axioms(
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
    """
    for view in views:
        # Get variables
        w = var_map[f"{view.name}.width"]
        h = var_map[f"{view.name}.height"]
        l = var_map[f"{view.name}.left"] # noqa: E741
        r = var_map[f"{view.name}.right"]
        t = var_map[f"{view.name}.top"]
        b = var_map[f"{view.name}.bottom"]
        cx = var_map[f"{view.name}.center_x"]
        cy = var_map[f"{view.name}.center_y"]

        # Add axioms (required strength)
        solver.addConstraint((w == r - l) | "required")
        solver.addConstraint((h == b - t) | "required")
        solver.addConstraint((cx == (l + r) / 2) | "required")
        solver.addConstraint((cy == (t + b) / 2) | "required")

        # Non-negative constraints
        solver.addConstraint((w >= 0) | "required")
        solver.addConstraint((h >= 0) | "required")
        solver.addConstraint((l >= 0) | "required")
        solver.addConstraint((t >= 0) | "required")


def constraint_to_kiwi(
    constraint: LinearConstraint, var_map: dict[str, kiwisolver.Variable]
) -> kiwisolver.Constraint:
    """Convert a LinearConstraint to a Kiwi constraint."""
    y_var = var_map[f"{constraint.y.view.name}.{constraint.y.type}"]

    if constraint.x is None:
        # Constant constraint: y = b
        return (y_var == float(constraint.b)) | "strong"
    else:
        # Linear constraint: y = a * x + b
        x_var = var_map[f"{constraint.x.view.name}.{constraint.x.type}"]

        # Handle Fraction for a
        if isinstance(constraint.a, Fraction):
            a_val = float(constraint.a)
        else:
            a_val = float(constraint.a)

        b_val = float(constraint.b)

        return (y_var == a_val * x_var + b_val) | "strong"


def solve_layout(
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
    var_map = {}
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
    add_layout_axioms(solver, root._flattened_views_in_subtree, var_map)

    # Add synthesized constraints
    for constraint in constraints:
        solver.addConstraint(constraint_to_kiwi(constraint, var_map))

    # Fix root dimensions to desired size
    solver.addConstraint((var_map[f"{root.name}.width"] == width) | "required")
    solver.addConstraint((var_map[f"{root.name}.height"] == height) | "required")
    solver.addConstraint((var_map[f"{root.name}.left"] == 0) | "required")
    solver.addConstraint((var_map[f"{root.name}.top"] == 0) | "required")

    # Solve
    solver.updateVariables()

    # Debug: Print solved values
    print(f"\nSolved layout for width={width}, height={height}:")
    for view in root._flattened_views_in_subtree:
        left = var_map[f"{view.name}.left"].value()
        right = var_map[f"{view.name}.right"].value()
        width_val = var_map[f"{view.name}.width"].value()
        print(
            f"  {view.name}: left={left:.2f}, right={right:.2f}, width={width_val:.2f}"
        )

    # Extract values
    return {key: var.value() for key, var in var_map.items()}


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Layout</title>
    <style>
        body {
            margin: 0;
            font-family: monospace;
        }
        .viewport {
            position: relative;
            background: #fafafa;
        }
        .view {
            position: absolute;
            box-sizing: border-box;
            border: 1px solid #333;
            padding: 4px;
            font-size: 11px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="viewport" style="width: {{ width }}px; height: {{ height }}px;">
        {% for view in views %}
        <div class="view" 
             style="left: {{ view.left }}px; 
                    top: {{ view.top }}px; 
                    width: {{ view.width }}px; 
                    height: {{ view.height }}px;">
            {{ view.name }}<br>{{ view.width }}×{{ view.height }}
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""


def visualize(
    hierarchy: View,
    constraints: list[LinearConstraint],
    width: int = 800,
    height: int = 600,
):
    """
    Visualize synthesized constraints at a specific screen size.

    Args:
        hierarchy: View hierarchy structure (just for view names/relationships)
        constraints: List of synthesized constraints
        width: Screen width (default: 800)
        height: Screen height (default: 600)
    """
    # Solve constraints
    solved_values = solve_layout(hierarchy, constraints, width, height)

    # Build view list
    views = []
    for view in hierarchy._flattened_views_in_subtree:
        left = solved_values[f"{view.name}.left"]
        top = solved_values[f"{view.name}.top"]
        right = solved_values[f"{view.name}.right"]
        bottom = solved_values[f"{view.name}.bottom"]

        views.append(
            {
                "name": view.name,
                "left": left,
                "top": top,
                "width": right - left,
                "height": bottom - top,
            }
        )

    # Render HTML
    template = Template(HTML_TEMPLATE)
    html = template.render(width=width, height=height, views=views)

    # Write to temp file and open in browser
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        f.write(html)
        temp_path = f.name

    print(f"Opening visualization at: {temp_path}")
    webbrowser.open(f"file://{temp_path}")
