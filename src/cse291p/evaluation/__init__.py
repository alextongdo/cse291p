"""Evaluation metrics for layout synthesis.

Implements RMSD and accuracy metrics from the Mockdown paper:
- RMSD: Root Mean Square Deviation of view corners between synthesized and original layouts
- Accuracy: Percentage of views within 1 pixel of original

Matches auto-mock's implementation in Tree.ts (using left, top, width, height).

Reimplements: mockdown/src/mockdown/evaluation/metrics.py (entire file)
"""

from .metrics import (
    get_view_ltwh,
    get_view_corners,
    calculate_rmsd,
    calculate_accuracy,
    evaluate_single_example,
    group_by_isomorphic_structure,
    evaluate_single_structure,
    evaluate_layouts
)

__all__ = [
    'get_view_ltwh',
    'get_view_corners',  # Backward compatibility
    'calculate_rmsd',
    'calculate_accuracy',
    'evaluate_single_example',
    'group_by_isomorphic_structure',
    'evaluate_single_structure',
    'evaluate_layouts'
]
