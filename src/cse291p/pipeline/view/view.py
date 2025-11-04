"""View concrete implementation.

Reimplements:
- mockdown/model/view/view.py (lines 14-193)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import chain
from typing import Iterator, Optional, Sequence, cast, List, Dict, Any, Iterable

from .types import IAnchor, IAnchorID, IEdge, IView, Anchor, Edge
from .primitives import Attribute, IRect, ViewName
from cse291p.types import NT


@dataclass(frozen=True, eq=True)
class View(IView[NT]):
    """Concrete view implementation.
    
    Reimplements: mockdown/model/view/view.py lines 14-193
    """
    name: ViewName
    rect: IRect[NT]
    children: Sequence[IView[NT]] = field(default_factory=list)
    parent: Optional[IView[NT]] = field(default=None, compare=False)

    # Note: parent must be excluded from comparisons, or we will get infinite recursion.

    # Anchor and Edge convenience properties (reimplements lines 24-78)
    @property
    def left_anchor(self) -> IAnchor[NT]:
        return Anchor(self, Attribute.LEFT)

    @property
    def left_edge(self) -> IEdge[NT]:
        return Edge(self.left_anchor, (self.top, self.bottom))

    @property
    def top_anchor(self) -> IAnchor[NT]:
        return Anchor(self, Attribute.TOP)

    @property
    def top_edge(self) -> IEdge[NT]:
        return Edge(self.top_anchor, (self.left, self.right))

    @property
    def right_anchor(self) -> IAnchor[NT]:
        return Anchor(self, Attribute.RIGHT)

    @property
    def right_edge(self) -> IEdge[NT]:
        return Edge(self.right_anchor, (self.top, self.bottom))

    @property
    def bottom_anchor(self) -> IAnchor[NT]:
        return Anchor(self, Attribute.BOTTOM)

    @property
    def bottom_edge(self) -> IEdge[NT]:
        return Edge(self.bottom_anchor, (self.left, self.right))

    @property
    def center_x_anchor(self) -> IAnchor[NT]:
        return Anchor(self, Attribute.CENTER_X)

    @property
    def center_x_edge(self) -> IEdge[NT]:
        return Edge(self.center_x_anchor, (self.top, self.bottom))

    @property
    def center_y_anchor(self) -> IAnchor[NT]:
        return Anchor(self, Attribute.CENTER_Y)

    @property
    def center_y_edge(self) -> IEdge[NT]:
        return Edge(self.center_y_anchor, (self.left, self.right))

    @property
    def width_anchor(self) -> IAnchor[NT]:
        return Anchor(self, Attribute.WIDTH)

    @property
    def height_anchor(self) -> IAnchor[NT]:
        return Anchor(self, Attribute.HEIGHT)

    @property
    def anchors(self) -> List[IAnchor[NT]]:
        """Reimplements: mockdown/model/view/view.py lines 81-83"""
        return [self.left_anchor, self.right_anchor, self.top_anchor, self.bottom_anchor, self.center_x_anchor,
                self.center_y_anchor, self.height_anchor, self.width_anchor]

    @property
    def x_anchors(self) -> List[IAnchor[NT]]:
        """Reimplements: mockdown/model/view/view.py lines 86-87"""
        return [self.left_anchor, self.right_anchor, self.width_anchor, self.center_x_anchor]

    @property
    def y_anchors(self) -> List[IAnchor[NT]]:
        """Reimplements: mockdown/model/view/view.py lines 89-91"""
        return [self.top_anchor, self.bottom_anchor, self.height_anchor, self.center_y_anchor]

    @property
    def all_anchors(self) -> Iterable[IAnchorID]:
        """Reimplements: mockdown/model/view/view.py lines 94-97"""
        yield from (anchor
                    for anchors in map(lambda v: v.anchors, iter(self))
                    for anchor in anchors)

    @property
    def all_anchor_ids(self) -> Iterable[IAnchor[NT]]:
        """Reimplements: mockdown/model/view/view.py lines 100-101"""
        yield from map(lambda a: a.id, self.all_anchors)

    @property
    def all_anchor_names(self) -> Iterable[str]:
        """Reimplements: mockdown/model/view/view.py lines 104-105"""
        yield from map(str, self.all_anchor_ids)

    def find_view(self,
                  name: ViewName,
                  include_self: bool = False,
                  deep: bool = False) -> Optional[IView[NT]]:
        """Get the first child element with the given name, or None.
        
        Reimplements: mockdown/model/view/view.py lines 107-128
        """
        try:
            if include_self and self.name == name:
                return self
            if deep:
                it = (child for child in chain(*self.children) if child.name == name)
                return next(it)
            else:
                it = (child for child in self.children if child.name == name)
                return next(it)
        except StopIteration:
            return None

    def find_anchor(self, anchor_id: IAnchorID) -> Optional[IAnchor[NT]]:
        """Reimplements: mockdown/model/view/view.py lines 130-137"""
        view_name = anchor_id.view_name
        attr = anchor_id.attribute

        view = self.find_view(view_name, include_self=True, deep=True)

        # Trust me, it's fine, I don't need to write out every case...
        return cast(IAnchor[NT], getattr(view, f"{attr.value}_anchor"))

    def is_parent_of(self, view: IView[NT]) -> bool:
        """Reimplements: mockdown/model/view/view.py lines 139-140"""
        return view.parent == self

    def is_parent_of_name(self, name: ViewName) -> bool:
        """Reimplements: mockdown/model/view/view.py lines 142-143"""
        return any([x.name == name for x in self.children])

    def is_child_of(self, view: IView[NT]) -> bool:
        """Reimplements: mockdown/model/view/view.py lines 145-146"""
        return self.parent == view

    def is_sibling_of(self, view: IView[NT]) -> bool:
        """Reimplements: mockdown/model/view/view.py lines 148-154"""
        comp = self.parent == view.parent
        if self.parent and view.parent and not comp:
            assert self.parent.name != view.parent.name, "unequal boxes with identical names %s, %s" % (
                self.parent.name, view.parent.name)

        return comp

    def is_isomorphic(self, view: IView[NT], include_names: bool = True) -> bool:
        """Graph/tree isomorphism. Useful for validating multiple samples as equivalent.
        
        Reimplements: mockdown/model/view/view.py lines 156-171
        """
        if len(self.children) != len(view.children):
            return False

        if include_names and self.name != view.name:
            return False

        if len(self.children) == 0:
            return True
        else:
            return all(c1.is_isomorphic(c2, include_names=include_names)
                       for c1, c2
                       in zip(self.children, view.children))

    def __iter__(self) -> Iterator[IView[NT]]:
        """Reimplements: mockdown/model/view/view.py lines 173-175"""
        yield self
        yield from chain(*map(lambda c: iter(c), self.children))

    def __repr__(self) -> str:
        """Reimplements: mockdown/model/view/view.py lines 177-178"""
        return f"View(name='{self.name}', rect={self.rect})"

    def to_dict(self) -> Dict[str, Any]:
        """Reimplements: mockdown/model/view/view.py lines 180-193"""
        def recur(it: IView[NT]) -> Dict[str, Any]:
            output: Dict[str, Any] = {}
            for anchor in it.anchors:
                output[anchor.attribute.value] = str(anchor.value)
            children = [c.to_dict() for c in it.children]
            output['children'] = children
            output['name'] = it.name
            return output

        out = recur(self)
        out['type'] = 'real'
        return out

