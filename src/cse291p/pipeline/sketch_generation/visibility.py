"""Visibility detection for sketch generation.

Reimplements:
- mockdown/src/mockdown/instantiation/visibility.py (lines 1-118)
"""

from collections import deque
from itertools import tee, chain
from operator import attrgetter
from typing import Iterable, Any, Tuple, List

from intervaltree import IntervalTree

from cse291p.pipeline.view import IView, IEdge
from cse291p.types import NT


def pairwise(iterable: Iterable[Any]) -> Iterable[Tuple[Any, Any]]:
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def interval_tree(root: IView[NT], primary_axis: str, include_root: bool = True) -> IntervalTree:
    """Compute an interval tree for the given root view and its immediate children.

    The primary axis is the axis along which the lines vary.
    The query axis is the other axis.
    
    Reimplements: mockdown/instantiation/visibility.py lines 18-49
    """
    assert primary_axis in ['x', 'y']

    tree = IntervalTree()

    view_iter = root.children
    if include_root:
        view_iter = list(chain([root], view_iter))

    for view in view_iter:
        if primary_axis == 'x':
            top_edge = view.top_edge
            bottom_edge = view.bottom_edge

            tree.addi(*top_edge.interval, top_edge)
            tree.addi(*bottom_edge.interval, bottom_edge)

        if primary_axis == 'y':
            left_edge = view.left_edge
            right_edge = view.right_edge

            tree.addi(*left_edge.interval, left_edge)
            tree.addi(*right_edge.interval, right_edge)

    return tree


def visible_pairs(view: IView[NT], deep: bool = True) -> List[Tuple[IEdge[NT], IEdge[NT]]]:
    """Compute visible edge pairs for the given view.

    Reimplements: mockdown/instantiation/visibility.py lines 52-118
    """
    root = view
    children = root.children

    # Build interval trees for horizontal and vertical line segments.
    # Do not include the root view, as it interferes with sorting later.
    x_itree = interval_tree(root, primary_axis='x', include_root=False)
    y_itree = interval_tree(root, primary_axis='y', include_root=False)

    # Events where we cast scan lines and check along them
    x_events = set(chain(*((view.left, view.right) for view in chain([root], children))))
    y_events = set(chain(*((view.top, view.bottom) for view in chain([root], children))))

    x_sort_key = attrgetter('view.center_x', 'position')
    y_sort_key = attrgetter('view.center_y', 'position')

    pairs: List[Tuple[IEdge[NT], IEdge[NT]]] = []

    for x_ev in x_events:
        # Cast a vertical line through horizontal intervals.
        data = deque(sorted(map(attrgetter('data'), x_itree[x_ev]), key=y_sort_key))
        data.appendleft(root.top_edge)
        data.append(root.bottom_edge)
        for pair in pairwise(data):
            if pair[0].view.name == pair[1].view.name:
                continue
            pairs.append(pair)
            pairs.append((pair[0].view.center_y_edge, pair[1].view.center_y_edge))

    for y_ev in y_events:
        # Cast a horizontal line through vertical intervals.
        data = deque(sorted(map(attrgetter('data'), y_itree[y_ev]), key=x_sort_key))
        data.appendleft(root.left_edge)
        data.append(root.right_edge)
        for pair in pairwise(data):
            if pair[0].view.name == pair[1].view.name:
                continue
            pairs.append(pair)
            pairs.append((pair[0].view.center_x_edge, pair[1].view.center_x_edge))

    if deep:
        for child in children:
            child_pairs = visible_pairs(child, deep=deep)
            pairs += child_pairs

    return pairs


