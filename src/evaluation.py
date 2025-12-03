"""
Evaluation metrics for synthesized layout constraints.
"""

import math
from typing import Dict, List

import kiwisolver

from src.render import (
    add_layout_axioms,
    constraint_to_kiwi,
)
from src.types import LinearConstraint, View


def calculate_rmsd(
    examples: List[View],
    outputs: Dict[tuple[int, ...], List[LinearConstraint]],
    debug: bool = False,
) -> float:
    """
    Calculate Root Mean Square Deviation (RMSD) between predicted and actual layouts.

    For each example:
    1. Determine which constraints apply (global + group-specific)
    2. Solve constraints for that example's screen size
    3. Compare predicted anchor positions with actual positions
    4. Compute RMSD across all anchors

    Args:
        examples: List of example views
        outputs: Dictionary mapping example index tuples to their constraints
                 e.g., {(0, 1): [constraints], (0, 1, 2, 3): [global constraints]}
        debug: If True, print debug information

    Returns:
        RMSD value (float)
    """
    if not examples:
        return 0.0

    root = examples[0]
    all_errors = []
    example_errors = []

    # Find global constraints (apply to all examples)
    global_key = tuple(range(len(examples)))
    global_constraints = outputs.get(global_key, [])

    # For each example, evaluate constraints
    for example_idx, example in enumerate(examples):
        # Find the most specific (smallest) group that contains this example
        # This ensures we use the correct group-specific constraints
        group_constraints = []
        candidate_groups = []
        
        for group_key, constraints in outputs.items():
            if group_key == global_key:
                continue
            if example_idx in group_key:
                candidate_groups.append((len(group_key), group_key, constraints))
        
        # Sort by group size (smallest first) to get most specific group
        if candidate_groups:
            candidate_groups.sort(key=lambda x: x[0])
            # Use the most specific (smallest) group
            _, _, group_constraints = candidate_groups[0]

        # Combine global and group-specific constraints
        all_constraints = global_constraints + group_constraints

        if not all_constraints:
            # No constraints, skip this example
            continue

        if debug:
            print(f"\nExample {example_idx}: Using {len(global_constraints)} global + "
                  f"{len(group_constraints)} group constraints")
            # Show some key constraints
            if group_constraints:
                print(f"  Sample group constraints:")
                for c in group_constraints[:5]:
                    print(f"    {c}")
                if len(group_constraints) > 5:
                    print(f"    ... and {len(group_constraints) - 5} more")

        # Solve constraints for this example's screen size
        # Use the example's own structure to ensure constraints are evaluated
        # in the correct context (even though structures are isomorphic,
        # using the actual example ensures proper evaluation)
        try:
            predicted_values = solve_layout_for_evaluation(
                example, all_constraints, example.width, example.height
            )
        except Exception as e:
            # If solving fails, skip this example
            print(f"Warning: Failed to solve constraints for example {example_idx}: {e}")
            continue

        # Compare predicted vs actual for all anchors
        # We iterate over the actual example's views to get ground truth values
        example_error_count = 0
        for view in example._flattened_views_in_subtree:
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
                anchor_key = f"{view.name}.{anchor_type}"

                # Get actual value
                if anchor_type == "left":
                    actual = view.left
                elif anchor_type == "right":
                    actual = view.right
                elif anchor_type == "top":
                    actual = view.top
                elif anchor_type == "bottom":
                    actual = view.bottom
                elif anchor_type == "width":
                    actual = view.width
                elif anchor_type == "height":
                    actual = view.height
                elif anchor_type == "center_x":
                    actual = view.center_x
                elif anchor_type == "center_y":
                    actual = view.center_y
                else:
                    continue

                # Get predicted value
                if anchor_key in predicted_values:
                    predicted = predicted_values[anchor_key]
                    error = predicted - actual
                    squared_error = error * error
                    all_errors.append(squared_error)  # squared error
                    example_error_count += 1
                    
                    if debug and abs(error) > 1.0:  # Only show significant errors
                        print(f"  {anchor_key}: predicted={predicted:.2f}, "
                              f"actual={actual:.2f}, error={error:.2f}")

        if debug:
            example_rmsd = math.sqrt(sum(all_errors[-example_error_count:]) / example_error_count) if example_error_count > 0 else 0.0
            example_errors.append((example_idx, example_error_count, example_rmsd))
            print(f"  Example {example_idx} RMSD: {example_rmsd:.4f} ({example_error_count} anchors)")

    # Calculate RMSD
    if not all_errors:
        return 0.0

    mse = sum(all_errors) / len(all_errors)
    rmsd = math.sqrt(mse)
    
    if debug:
        print(f"\nTotal: {len(all_errors)} anchor comparisons")
        print(f"Overall RMSD: {rmsd:.4f}")
    
    return rmsd


def solve_layout_for_evaluation(
    root: View, constraints: List[LinearConstraint], width: float, height: float
) -> Dict[str, float]:
    """
    Solve constraints for a specific screen size (for evaluation).

    Similar to solve_layout in render.py but without debug output.

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

    # Extract values
    return {key: var.value() for key, var in var_map.items()}

