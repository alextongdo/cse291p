import math

from src.types import View


def calculate_rmsd(
    predicted: dict[str, tuple[float, float, float, float]],
    ground_truth: View,
) -> float:
    """
    Calculate Root Mean Square Deviation (RMSD) between predicted and actual layouts.
    """
    all_squared_errors: list[float] = []

    for view in ground_truth._flattened_views_in_subtree:
        pred_left, pred_top, pred_right, pred_bottom = predicted[view.name]
        all_squared_errors.extend(
            [
                (pred_left - view.left) ** 2,
                (pred_top - view.top) ** 2,
                (pred_right - view.right) ** 2,
                (pred_bottom - view.bottom) ** 2,
            ]
        )

    mse = sum(all_squared_errors) / len(all_squared_errors)
    return math.sqrt(mse)
