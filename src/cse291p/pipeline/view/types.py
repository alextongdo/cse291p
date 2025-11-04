"""View hierarchy types and interfaces.

Reimplements:
- mockdown/model/types.py lines 36-190 (IView, IAnchor, IEdge, IAnchorID protocols)
- mockdown/model/anchor.py lines 12-58 (AnchorID, Anchor implementations)
- mockdown/model/edge.py lines 9-30 (Edge implementation)
"""

from __future__ import annotations
import re
from typing import Protocol, Optional, Sequence, Iterator, List, Iterable, Tuple, cast, Any
from abc import abstractmethod
from dataclasses import dataclass
from .primitives import ViewName, IRect, Attribute
from cse291p.types import NT


class IAnchorID(Protocol):
    """Anchor identifier protocol.
    
    Reimplements: mockdown/model/anchor.py lines 12-29 (AnchorID structure)
    """
    view_name: ViewName
    attribute: Attribute


class IAnchor(Protocol[NT]):
    """Anchor protocol - a specific attribute of a view.
    
    Reimplements: mockdown/model/types.py (implicit protocol from IView anchor properties)
    """
    view: 'IView[NT]'
    attribute: Attribute
    
    @property
    @abstractmethod
    def id(self) -> IAnchorID: ...
    
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def value(self) -> NT: ...


class IEdge(Protocol[NT]):
    """Edge protocol - represents a line segment of a view.
    
    Reimplements: mockdown/model/types.py lines 36-50
    """
    anchor: IAnchor[NT]
    interval: Tuple[NT, NT]
    
    @property
    @abstractmethod
    def position(self) -> NT: ...


class IView(Protocol[NT]):
    """View interface - represents a UI element with position and children.
    
    Reimplements: mockdown/model/types.py lines 53-190
    """
    name: ViewName
    rect: IRect[NT]
    children: Sequence['IView[NT]']
    parent: Optional['IView[NT]']

    # Delegate rect properties (reimplements lines 59-91)
    @property
    def left(self) -> NT:
        return self.rect.left

    @property
    def top(self) -> NT:
        return self.rect.top

    @property
    def right(self) -> NT:
        return self.rect.right

    @property
    def bottom(self) -> NT:
        return self.rect.bottom

    @property
    def width(self) -> NT:
        return self.rect.width

    @property
    def height(self) -> NT:
        return self.rect.height

    @property
    def center_x(self) -> NT:
        return self.rect.center_x

    @property
    def center_y(self) -> NT:
        return self.rect.center_y

    # Anchor properties (reimplements lines 109-138)
    @property
    @abstractmethod
    def left_anchor(self) -> IAnchor[NT]: ...

    @property
    @abstractmethod
    def top_anchor(self) -> IAnchor[NT]: ...

    @property
    @abstractmethod
    def right_anchor(self) -> IAnchor[NT]: ...

    @property
    @abstractmethod
    def bottom_anchor(self) -> IAnchor[NT]: ...

    @property
    @abstractmethod
    def width_anchor(self) -> IAnchor[NT]: ...

    @property
    @abstractmethod
    def height_anchor(self) -> IAnchor[NT]: ...

    @property
    @abstractmethod
    def center_x_anchor(self) -> IAnchor[NT]: ...

    @property
    @abstractmethod
    def center_y_anchor(self) -> IAnchor[NT]: ...

    # Edge properties (reimplements lines 93-107)
    @property
    @abstractmethod
    def left_edge(self) -> IEdge[NT]: ...

    @property
    @abstractmethod
    def top_edge(self) -> IEdge[NT]: ...

    @property
    @abstractmethod
    def right_edge(self) -> IEdge[NT]: ...

    @property
    @abstractmethod
    def bottom_edge(self) -> IEdge[NT]: ...

    # Additional properties (reimplements lines 139-151)
    @property
    @abstractmethod
    def anchors(self) -> List[IAnchor[NT]]: ...

    @property
    @abstractmethod
    def x_anchors(self) -> List[IAnchor[NT]]: ...

    @property
    @abstractmethod
    def y_anchors(self) -> List[IAnchor[NT]]: ...

    @property
    @abstractmethod
    def all_anchors(self) -> Iterable[IAnchorID]: ...

    @property
    @abstractmethod
    def all_anchor_ids(self) -> Iterable[IAnchor[NT]]: ...

    @property
    @abstractmethod
    def all_anchor_names(self) -> Iterable[str]: ...

    # Methods (reimplements lines 165-190)
    def find_view(self, name: ViewName, include_self: bool = False, deep: bool = False) -> Optional['IView[NT]']: ...
    def find_anchor(self, anchor_id: IAnchorID) -> Optional[IAnchor[NT]]: ...
    def is_parent_of(self, view: 'IView[NT]') -> bool: ...
    def is_parent_of_name(self, name: ViewName) -> bool: ...
    def is_child_of(self, view: 'IView[NT]') -> bool: ...
    def is_sibling_of(self, view: 'IView[NT]') -> bool: ...
    def is_isomorphic(self, view: 'IView[NT]', include_names: bool = True) -> bool: ...
    def __iter__(self) -> Iterator['IView[NT]']: ...
    def to_dict(self) -> dict[str, Any]: ...


@dataclass(frozen=True, eq=True, order=True)
class AnchorID(IAnchorID):
    """Concrete anchor identifier.
    
    Reimplements: mockdown/model/anchor.py lines 12-29
    """
    view_name: ViewName
    attribute: Attribute

    @classmethod
    def from_str(cls, s: str) -> Optional['AnchorID']:
        """Reimplements: mockdown/model/anchor.py lines 17-26"""
        if s == 'None':
            return None

        if (m := re.match(r'(\w+)\.(\w+)', s)) is None:
            raise Exception(f"{s} is not a valid anchor ID string.")

        v, a = m.groups()
        return cls(view_name=v, attribute=Attribute(a))

    def __str__(self) -> str:
        """Reimplements: mockdown/model/anchor.py lines 28-29"""
        return f"{self.view_name}.{self.attribute.value}"


@dataclass(frozen=True, order=True)
class Anchor(IAnchor[NT]):
    """Concrete anchor implementation.
    
    Reimplements: mockdown/model/anchor.py lines 32-58
    """
    view: IView[NT]
    attribute: Attribute

    @property
    def id(self) -> IAnchorID:
        """Reimplements: mockdown/model/anchor.py lines 42-43"""
        return AnchorID(self.view.name, self.attribute)

    @property
    def name(self) -> str:
        """Reimplements: mockdown/model/anchor.py lines 45-47"""
        return f"{self.view.name}.{self.attribute.value}"

    @property
    def value(self) -> NT:
        """Reimplements: mockdown/model/anchor.py lines 49-51"""
        return cast(NT, getattr(self.view, self.attribute.value))

    @property
    def edge(self) -> IEdge[NT]:
        """Reimplements: mockdown/model/anchor.py lines 53-55"""
        return cast(IEdge[NT], getattr(self.view, f"{self.attribute.value}_edge"))

    def __repr__(self) -> str:
        """Reimplements: mockdown/model/anchor.py lines 57-58"""
        return f"{self.name} @ {self.value}"


@dataclass(frozen=True)
class Edge(IEdge[NT]):
    """Concrete edge implementation.
    
    Reimplements: mockdown/model/edge.py lines 9-30
    """
    anchor: IAnchor[NT]
    interval: Tuple[NT, NT]

    @property
    def view(self) -> IView[NT]:
        """Reimplements: mockdown/model/edge.py lines 15-16"""
        return self.anchor.view

    @property
    def attribute(self) -> Attribute:
        """Reimplements: mockdown/model/edge.py lines 18-20"""
        return self.anchor.attribute

    @property
    def position(self) -> NT:
        """Reimplements: mockdown/model/edge.py lines 22-24"""
        return self.anchor.value

    def __post_init__(self) -> None:
        """Reimplements: mockdown/model/edge.py lines 26-27"""
        assert self.interval[0] <= self.interval[1]

    def __repr__(self) -> str:
        """Reimplements: mockdown/model/edge.py lines 29-30"""
        return f"{self.view.name}.{self.attribute.value} {self.interval} @ {self.position}"
