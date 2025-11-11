# Template Instantiation
# Given a view hierarchy, generate constraint sketches with unknown parameters.
# Uses vectorized matrix operations to efficiently identify valid anchor pairs.

import numpy as np
from intervaltree import IntervalTree

from src.types import Anchor, LinearConstraint, View


def compute_visibility_matrix(anchors: list[Anchor], root: View) -> np.ndarray:
    """
    Compute NxN visibility matrix using sweep-line algorithm with IntervalTree.

    Algorithm:
    1. Build interval trees for horizontal/vertical edges
    2. Cast sweep lines at every view boundary coordinate
    3. Edges adjacent along a sweep line are visible to each other
    """
    n = len(anchors)
    visible_matrix = np.zeros((n, n), dtype=bool)

    # Index anchors by view and type to preserve across examples
    anchor_to_index_map = {
        (anchor.view.name, anchor.type): i for i, anchor in enumerate(anchors)
    }

    # Stores horizontal edges of the form y = c {left <= x <= right}
    # When queried by x = c, returns intersecting edges
    horizontal_edge_tree = IntervalTree()
    # Stores vertical edges of the form x = c {top <= y <= bottom}
    # When queried by y = c, returns intersecting edges
    vertical_edge_tree = IntervalTree()

    # Don't consider root view since it always intersects with all other views
    views = [v for v in root._flattened_views_in_subtree if v != root]

    # Collect all y-coords to cast horizontal intersection lines y = c
    horizontal_events = set()
    # Collect all x-coords to cast vertical intersection lines x = c
    vertical_events = set()

    # Add sweep lines at root's edges in case some children are touching
    horizontal_events.add(root.rect[1])  # top
    horizontal_events.add(root.rect[3])  # bottom
    vertical_events.add(root.rect[0])  # left
    vertical_events.add(root.rect[2])  # right

    for view in views:
        left, top, right, bottom = view.rect
        # Top edge
        horizontal_edge_tree.addi(begin=left, end=right, data=view.anchor("top"))
        # Bottom edge
        horizontal_edge_tree.addi(begin=left, end=right, data=view.anchor("bottom"))

        horizontal_events.add(top)
        horizontal_events.add(bottom)

        # Left edge
        vertical_edge_tree.addi(begin=top, end=bottom, data=view.anchor("left"))
        # Right edge
        vertical_edge_tree.addi(begin=top, end=bottom, data=view.anchor("right"))

        vertical_events.add(left)
        vertical_events.add(right)

    for vertical_line in vertical_events:
        intersecting_anchors: list[Anchor] = [
            interval.data for interval in horizontal_edge_tree[vertical_line]
        ]
        # Original Mockdown sorts by view.center_y, then by anchor position
        intersecting_anchors.sort(
            key=lambda anchor: (
                (anchor.view.rect[1] + anchor.view.rect[3]) / 2,  # view.center_y
                (
                    anchor.view.rect[1] if anchor.type == "top" else anchor.view.rect[3]
                ),  # position
            )
        )

        # Root edges will always start and end the intersecting anchors
        intersecting_anchors.insert(0, root.anchor("top"))
        intersecting_anchors.append(root.anchor("bottom"))

        # Adjacent anchors are visible
        for i in range(len(intersecting_anchors) - 1):
            anchor_i = intersecting_anchors[i]
            anchor_j = intersecting_anchors[i + 1]
            # We should not have duplicate anchors here
            assert anchor_i != anchor_j
            # Skip meaningless anchors pairs from same view
            if anchor_i.view.name == anchor_j.view.name:
                continue

            # Mark the edge anchors as visible
            idx_i = anchor_to_index_map[(anchor_i.view.name, anchor_i.type)]
            idx_j = anchor_to_index_map[(anchor_j.view.name, anchor_j.type)]
            visible_matrix[idx_i, idx_j] = True
            visible_matrix[idx_j, idx_i] = True  # Symmetric

            # Also mark center_y anchors of adjacent views as visible
            center_y_i = anchor_to_index_map[(anchor_i.view.name, "center_y")]
            center_y_j = anchor_to_index_map[(anchor_j.view.name, "center_y")]
            visible_matrix[center_y_i, center_y_j] = True
            visible_matrix[center_y_j, center_y_i] = True

    for horizontal_line in horizontal_events:
        intersecting_anchors: list[Anchor] = [
            interval.data for interval in vertical_edge_tree[horizontal_line]
        ]
        # Original Mockdown sorts by view.center_x, then by anchor position
        intersecting_anchors.sort(
            key=lambda anchor: (
                (anchor.view.rect[0] + anchor.view.rect[2]) / 2,  # view.center_x
                (
                    anchor.view.rect[0]
                    if anchor.type == "left"
                    else anchor.view.rect[2]
                ),  # position
            )
        )

        # Root edges will always start and end the intersecting anchors
        intersecting_anchors.insert(0, root.anchor("left"))
        intersecting_anchors.append(root.anchor("right"))

        # Adjacent anchors are visible
        for i in range(len(intersecting_anchors) - 1):
            anchor_i = intersecting_anchors[i]
            anchor_j = intersecting_anchors[i + 1]
            # We should not have duplicate anchors here
            assert anchor_i != anchor_j
            # Skip meaningless anchors pairs from same view
            if anchor_i.view.name == anchor_j.view.name:
                continue

            # Mark the edge anchors as visible
            idx_i = anchor_to_index_map[(anchor_i.view.name, anchor_i.type)]
            idx_j = anchor_to_index_map[(anchor_j.view.name, anchor_j.type)]
            visible_matrix[idx_i, idx_j] = True
            visible_matrix[idx_j, idx_i] = True  # Symmetric

            # Also mark center_x anchors of adjacent views as visible
            center_x_i = anchor_to_index_map[(anchor_i.view.name, "center_x")]
            center_x_j = anchor_to_index_map[(anchor_j.view.name, "center_x")]
            visible_matrix[center_x_i, center_x_j] = True
            visible_matrix[center_x_j, center_x_i] = True

    return visible_matrix


def template_instantiation(examples: list[View]) -> list[LinearConstraint]:
    """
    Returns constraint sketches with unknown parameters:
    - For aspect ratios: a is unknown, b=0
    - For parent-relative sizes: a is unknown, b=0
    - For absolute sizes: a=0, b is unknown (x=None for constants)
    - For offsets: a=1, b is unknown
    """
    sketches = []

    # Assumes all examples have the same hierarchy structure (isomorphic)
    anchors: list[Anchor] = examples[0]._anchors_in_subtree
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

    # Compute visibility matrix for all examples
    visible_matrix = np.zeros((n, n), dtype=bool)
    for example in examples:
        example_visible_matrix = compute_visibility_matrix(anchors, example)
        visible_matrix |= example_visible_matrix

    for i in range(n):
        for j in range(n):
            same_view_matrix[i, j] = anchors[i].view == anchors[j].view
            same_type_matrix[i, j] = anchors[i].type == anchors[j].type
            # Column is parent of row so that parent = a * child + b
            parent_matrix[i, j] = anchors[j].view in anchors[i].view.children
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
            dual_type_matrix[i, j] = {anchors[i].type, anchors[j].type} == {
                "left",
                "right",
            } or {anchors[i].type, anchors[j].type} == {"top", "bottom"}

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
