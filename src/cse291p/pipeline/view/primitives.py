"""View primitives (Rect, Attribute, ViewName).

Reimplements:
- mockdown/model/primitives/attribute.py (lines 8-67)
- mockdown/model/primitives/geometry.py (lines 10-57)
- mockdown/model/primitives/identifiers.py (lines 4)
"""

from __future__ import annotations
from typing import Protocol, FrozenSet, Any, TypeVar
from enum import Enum
from dataclasses import dataclass
from abc import abstractmethod

# Type variable for numeric types (reimplements mockdown/types.py line 16)
NT = TypeVar('NT')

# Type alias for view names (reimplements mockdown/model/primitives/identifiers.py line 4)
ViewName = str


class Attribute(Enum):
    """View attributes for anchors and constraints.
    
    Reimplements: mockdown/model/primitives/attribute.py lines 8-67
    """
    LEFT = 'left'
    TOP = 'top'
    RIGHT = 'right'
    BOTTOM = 'bottom'
    CENTER_X = 'center_x'
    CENTER_Y = 'center_y'
    WIDTH = 'width'
    HEIGHT = 'height'

    def is_compatible(self, other: Attribute) -> bool:
        """Reimplements: mockdown/model/primitives/attribute.py lines 18-22"""
        s_attrs = {Attribute.WIDTH, Attribute.HEIGHT}
        return self in h_attrs and other in h_attrs \
               or self in v_attrs and other in v_attrs \
               or self in s_attrs and other in s_attrs

    def is_size(self) -> bool:
        """Reimplements: mockdown/model/primitives/attribute.py lines 24-25"""
        return self in {Attribute.WIDTH, Attribute.HEIGHT}

    def is_position(self) -> bool:
        """Reimplements: mockdown/model/primitives/attribute.py lines 27-29"""
        return self in {Attribute.LEFT, Attribute.TOP, Attribute.RIGHT, Attribute.BOTTOM,
                        Attribute.CENTER_X, Attribute.CENTER_Y}

    def is_horizontal(self) -> bool:
        """Reimplements: mockdown/model/primitives/attribute.py lines 31-32"""
        return self in {Attribute.LEFT, Attribute.RIGHT, Attribute.CENTER_X, Attribute.WIDTH}

    def is_vertical(self) -> bool:
        """Reimplements: mockdown/model/primitives/attribute.py lines 34-35"""
        return self in {Attribute.TOP, Attribute.BOTTOM, Attribute.CENTER_Y, Attribute.HEIGHT}

    @staticmethod
    def is_dual_pair(a1: Attribute, a2: Attribute):
        """Reimplements: mockdown/model/primitives/attribute.py lines 37-43"""
        if a1 == Attribute.RIGHT and a2 == Attribute.LEFT:
            return True
        if a1 == Attribute.BOTTOM and a2 == Attribute.TOP:
            return True
        return False

    # Comparison methods (reimplements lines 45-63)
    def __ge__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


# Attribute groupings (reimplements mockdown/model/primitives/attribute.py lines 66-67)
h_attrs: FrozenSet[Attribute] = frozenset({
    Attribute.LEFT, Attribute.RIGHT, Attribute.CENTER_X, Attribute.WIDTH
})

v_attrs: FrozenSet[Attribute] = frozenset({
    Attribute.TOP, Attribute.BOTTOM, Attribute.CENTER_Y, Attribute.HEIGHT
})


class IRect(Protocol[NT]):
    """Rectangle interface.
    
    Reimplements: mockdown/model/primitives/geometry.py lines 10-30
    """
    left: NT
    top: NT
    right: NT
    bottom: NT
    
    @property
    @abstractmethod
    def width(self) -> NT: ...
    
    @property
    @abstractmethod
    def height(self) -> NT: ...
    
    @property
    @abstractmethod
    def center_x(self) -> NT: ...
    
    @property
    @abstractmethod
    def center_y(self) -> NT: ...


@dataclass(frozen=True, eq=True)
class Rect(IRect[NT]):
    """Concrete rectangle implementation.
    
    Reimplements: mockdown/model/primitives/geometry.py lines 33-57
    """
    left: NT
    top: NT
    right: NT
    bottom: NT

    @property
    def width(self) -> NT:
        """Reimplements: mockdown/model/primitives/geometry.py lines 44-45"""
        return self.right - self.left

    @property
    def height(self) -> NT:
        """Reimplements: mockdown/model/primitives/geometry.py lines 47-49"""
        return self.bottom - self.top

    @property
    def center_x(self) -> NT:
        """Reimplements: mockdown/model/primitives/geometry.py lines 51-53"""
        return (self.left + self.right) / 2

    @property
    def center_y(self) -> NT:
        """Reimplements: mockdown/model/primitives/geometry.py lines 55-57"""
        return (self.top + self.bottom) / 2
