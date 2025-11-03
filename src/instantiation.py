# Template Instantiation
# Given a view hierarchy, generate constraint sketches with unknown parameters.
# Uses vectorized matrix operations to efficiently identify valid anchor pairs.

import numpy as np

from src.types import Anchor, LinearConstraint, View


def compute_visibility_matrix(anchors: list[Anchor], root: View) -> np.ndarray:
    """
    Compute NxN visibility matrix. Uses IntervalTree sweep-line algorithm.
    """
    pass


def template_instantiation(root: View) -> list[LinearConstraint]:
    """
    Returns constraint sketches with unknown parameters:
    - For aspect ratios: a is unknown, b=0
    - For parent-relative sizes: a is unknown, b=0
    - For absolute sizes: a=0, b is unknown (x=None for constants)
    - For offsets: a=1, b is unknown
    """
    sketches = []
    anchors: list[Anchor] = root._anchors_in_subtree
    n = len(anchors)

    # Use boolean matrices to efficiently combine
    # various predicates over anchor pairs
    same_view_matrix = np.zeros((n, n), dtype=bool)
    same_type_matrix = np.zeros((n, n), dtype=bool)
    parent_matrix = np.zeros((n, n), dtype=bool)
    sibling_matrix = np.zeros((n, n), dtype=bool)
    both_size_matrix = np.zeros((n, n), dtype=bool)
    both_position_matrix = np.zeros((n, n), dtype=bool)
    both_horizontal_matrix = np.zeros((n, n), dtype=bool)
    both_vertical_matrix = np.zeros((n, n), dtype=bool)
    one_horizontal_one_vertical_matrix = np.zeros((n, n), dtype=bool)
    dual_type_matrix = np.zeros((n, n), dtype=bool)
    visible_matrix = compute_visibility_matrix(anchors, root)

    for i in range(n):
        for j in range(n):
            same_view_matrix[i, j] = anchors[i].view == anchors[j].view
            same_type_matrix[i, j] = anchors[i].type == anchors[j].type
            parent_matrix[i, j] = anchors[i].view in anchors[j].view.children
            sibling_matrix[i, j] = (
                anchors[i].view != anchors[j].view
                and anchors[i].view.parent == anchors[j].view.parent
            )
            both_size_matrix[i, j] = anchors[i].is_size() and anchors[j].is_size()
            both_position_matrix[i, j] = (
                anchors[i].is_position() and anchors[j].is_position()
            )
            both_horizontal_matrix[i, j] = (
                anchors[i].is_horizontal() and anchors[j].is_horizontal()
            )
            both_vertical_matrix[i, j] = (
                anchors[i].is_vertical() and anchors[j].is_vertical()
            )
            one_horizontal_one_vertical_matrix[i, j] = (
                anchors[i].is_horizontal() and anchors[j].is_vertical()
            )
            dual_type_matrix[i, j] = (
                {anchors[i].type, anchors[j].type} == {"left", "right"}
                or {anchors[i].type, anchors[j].type} == {"top", "bottom"}
            )

    # Aspect Ratio Constraints: (y = a * x)
    # y and x are from same view and y = [anchor].width; x = [anchor].height
    aspect_ratio_matrix = (
        same_view_matrix & both_size_matrix & one_horizontal_one_vertical_matrix
    )

    # Parent-Relative Size Constraints: (y = a * x)
    # y = [child].width/height; x = [parent].width/height
    parent_relative_matrix = (
        parent_matrix
        & both_size_matrix
        & (both_horizontal_matrix | both_vertical_matrix)
    )

    # Offset Position Constraints: (y = x + b)
    # y = [parent].[same_type]; x = [child].[same_type]
    # y = [sibling].[left/right]; x = [sibling].[right/left]
    # y = [sibling].[top/bottom]; x = [sibling].[bottom/top]
    # and anchors are visible from each other
    offset_parent_child_matrix = (
        parent_matrix & both_position_matrix & same_type_matrix & visible_matrix
    )
    offset_sibling_matrix = (
        sibling_matrix & both_position_matrix & dual_type_matrix & visible_matrix
    )
    offset_matrix = offset_parent_child_matrix | offset_sibling_matrix

    # Alignment Position Constraints: (y = x)
    # y = [sibling].[left/right]; x = [sibling].[left/right]
    # y = [sibling].[top/bottom]; x = [sibling].[top/bottom]
    # y = [sibling].[center_x/center_y]; x = [sibling].[center_x/center_y]
    # and anchors are visible from each other
    alignment_horizontal_matrix = (
        sibling_matrix
        & both_horizontal_matrix
        & both_position_matrix
        & same_type_matrix
        & visible_matrix
    )
    alignment_vertical_matrix = (
        sibling_matrix
        & both_vertical_matrix
        & both_position_matrix
        & same_type_matrix
        & visible_matrix
    )
    alignment_matrix = alignment_horizontal_matrix | alignment_vertical_matrix

    for i in range(n):
        for j in range(n):
            if aspect_ratio_matrix[i, j]:
                sketches.append(
                    LinearConstraint(y=anchors[i], x=anchors[j], a=None, b=0.0),
                )
            if parent_relative_matrix[i, j]:
                sketches.append(
                    LinearConstraint(
                        y=anchors[i],
                        x=anchors[j],
                        a=None,
                        b=0.0,
                    ),
                )
            if offset_matrix[i, j] or alignment_matrix[i, j]:
                # Technically alignment should enfoce b=0, but 
                # original Mockdown allows small alignment errors
                sketches.append(
                    LinearConstraint(y=anchors[i], x=anchors[j], a=1.0, b=None),
                )

    # Constant Constraints: (y = b)
    # y = [anchor].width/height
    for i in range(n):
        if anchors[i].is_size():
            sketches.append(LinearConstraint(y=anchors[i], x=None, a=0.0, b=None))

    return sketches
