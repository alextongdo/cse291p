"""ViewBuilder for constructing view hierarchies.

Reimplements:
- mockdown/model/view/builder.py (lines 1-52)
- mockdown/model/view/types.py (lines 1-8)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, Sequence, cast, Type, Tuple, List, Union
from numbers import Number as PyNumber
import sympy as sym

from .primitives import IRect, ViewName, Rect
from .types import IView
from .view import View
from cse291p.types import NT


# This is a set of types that sympy.Number's constructor will accept.
# Reimplements: mockdown/model/view/types.py lines 1-6
NumberConvertible = Union[str, int, float, sym.Number]


class IViewBuilder(Protocol):
    """View builder protocol.
    
    Reimplements: mockdown/model/view/builder.py lines 21-28
    """
    name: ViewName
    rect: Tuple[NumberConvertible, NumberConvertible, NumberConvertible, NumberConvertible]
    children: Sequence[IViewBuilder]
    parent: Optional[IViewBuilder]

    def build(self, number_type: Type[NT], parent_view: Optional[IView[NT]] = None) -> IView[NT]: ...


@dataclass
class ViewBuilder(IViewBuilder):
    """Concrete view builder.
    
    Reimplements: mockdown/model/view/builder.py lines 31-52
    """
    name: ViewName
    rect: Tuple[NumberConvertible, NumberConvertible, NumberConvertible, NumberConvertible]
    children: Sequence[IViewBuilder] = field(default_factory=list)
    parent: Optional[IViewBuilder] = field(default=None)

    # Note: NT is _not_ bound at the class level, the universal quantifier over NT is on the method!
    # This method is dependently typed, and is parametrized by the numeric type (as a value).
    def build(self, number_type: Type[NT], parent_view: Optional[IView[NT]] = None) -> IView[NT]:
        """Reimplements: mockdown/model/view/builder.py lines 40-48"""
        view: IView[NT] = View(name=self.name,
                               rect=self._make_rect(number_type),
                               parent=parent_view)

        child_views = [child.build(number_type=number_type, parent_view=view) for child in self.children]
        object.__setattr__(cast(object, view), 'children', child_views)

        return view

    def _make_rect(self, number_type: Type[NT]) -> IRect[NT]:
        """Reimplements: mockdown/model/view/builder.py lines 50-52"""
        args: List[NT] = [number_type(v) for v in self.rect]
        return Rect(*args)
