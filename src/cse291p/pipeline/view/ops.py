"""View operations (isomorphism, traversal).

This module contains utility functions for working with view hierarchies.
Most operations are methods on the View class itself, but this provides
additional utilities and clear separation of concerns.

Reimplements functionality from:
- mockdown/model/view/view.py (isomorphism, traversal methods)
"""

from typing import Iterator, Optional
from .types import IView, ViewName


def traverse(view: IView, include_self: bool = True, deep: bool = True) -> Iterator[IView]:
    """Traverse a view hierarchy.
    
    Reimplements: mockdown/model/view/view.py __iter__ method (lines 173-175)
    """
    if include_self:
        yield view
    
    if deep:
        for child in view.children:
            yield from traverse(child, include_self=True, deep=True)
    else:
        yield from view.children


def find_view(view: IView, name: ViewName, include_self: bool = False, deep: bool = False) -> Optional[IView]:
    """Find a view by name in the hierarchy.
    
    Reimplements: mockdown/model/view/view.py find_view method (lines 107-128)
    """
    return view.find_view(name, include_self=include_self, deep=deep)


def is_isomorphic(a: IView, b: IView, include_names: bool = True) -> bool:
    """Check if two view hierarchies are isomorphic.
    
    Reimplements: mockdown/model/view/view.py is_isomorphic method (lines 156-171)
    """
    return a.is_isomorphic(b, include_names=include_names)
