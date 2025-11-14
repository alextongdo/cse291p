from typing import Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr


class View(BaseModel):
    name: str
    rect: tuple[float, float, float, float]
    children: list["View"] = Field(default_factory=list)
    parent: Optional["View"] = None

    _anchors_in_subtree: list["Anchor"] = PrivateAttr(default_factory=list)
    _flattened_views_in_subtree: list["View"] = PrivateAttr(default_factory=list)

    def anchor(self, type: str) -> "Anchor":
        return Anchor(view=self, type=type)

    def __eq__(self, other) -> bool:
        if not isinstance(other, View):
            return False
        return self.name == other.name and self.rect == other.rect

    def model_post_init(self, _):
        anchors = self.anchors()
        views = [self]
        for child in self.children:
            child.parent = self
            child.model_post_init(_)
            anchors.extend(child._anchors_in_subtree)
            views.extend(child._flattened_views_in_subtree)
        self._anchors_in_subtree = anchors
        self._flattened_views_in_subtree = views

    def anchors(self) -> list["Anchor"]:
        """Get all anchors for this view."""
        return [
            Anchor(view=self, type="left"),
            Anchor(view=self, type="right"),
            Anchor(view=self, type="top"),
            Anchor(view=self, type="bottom"),
            Anchor(view=self, type="center_x"),
            Anchor(view=self, type="center_y"),
            Anchor(view=self, type="width"),
            Anchor(view=self, type="height"),
        ]


class Anchor(BaseModel):
    """
    Represents an anchor point in a view.
    """

    view: View
    type: Literal[
        "left",
        "right",
        "top",
        "bottom",
        "center_x",
        "center_y",
        "width",
        "height",
    ]

    def __eq__(self, other) -> bool:
        """Compare based on view name and type to avoid infinite recursion."""
        if not isinstance(other, Anchor):
            return False
        # Assumes that view names are unique,
        # i.e. View objects with the same name are equivalent
        return self.view.name == other.view.name and self.type == other.type

    def is_size(self) -> bool:
        """Check if anchor is a size type (width or height)."""
        return self.type in ["width", "height"]

    def is_position(self) -> bool:
        """
        Check if anchor is a position type (left, top, right, bottom, center_x,
        center_y).
        """
        return self.type in ["left", "top", "right", "bottom", "center_x", "center_y"]

    def is_horizontal(self) -> bool:
        """Check if anchor is a horizontal type (left, right, center_x, width)."""
        return self.type in ["left", "right", "center_x", "width"]

    def is_vertical(self) -> bool:
        """Check if anchor is a vertical type (top, bottom, center_y, height)."""
        return self.type in ["top", "bottom", "center_y", "height"]


class LinearConstraint(BaseModel):
    """
    Constraint of the form y = a * x + b. Both a and b may be 0.
    """

    y: Anchor
    x: Anchor | None = None  # None means y = b
    a: float | None = None  # None means not yet known
    b: float | None = None  # None means not yet known

    def __repr__(self) -> str:
        if self.x is None:
            assert self.a == 0
            return (
                f"LinearConstraint({self.y.view.name}.{self.y.type} = {self.b or 'b'})"
            )
        return (
            f"LinearConstraint({self.y.view.name}.{self.y.type} = "
            f"{self.a if self.a is not None else 'a'} * "
            f"{self.x.view.name}.{self.x.type} + "
            f"{self.b if self.b is not None else 'b'})"
        )
