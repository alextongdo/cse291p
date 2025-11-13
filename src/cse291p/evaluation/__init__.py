"""Evaluation metrics for layout synthesis.

Implements RMSD and accuracy metrics from the Mockdown paper:
- RMSD: Root Mean Square Deviation of view corners between synthesized and original layouts
- Accuracy: Percentage of views within one pixel of the original layout

Supports both single-structure layouts and conditional layouts (with structural variations).
"""

from .metrics import (
    get_view_corners,
    calculate_rmsd,
    calculate_accuracy,
    evaluate_single_example,
    evaluate_single_structure,
    group_by_isomorphic_structure,
    evaluate_layouts,
)

__all__ = [
    'get_view_corners',
    'calculate_rmsd',
    'calculate_accuracy',
    'evaluate_single_example',
    'evaluate_single_structure',
    'group_by_isomorphic_structure',
    'evaluate_layouts',
]

