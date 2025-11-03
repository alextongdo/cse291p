from typing import Literal

from pydantic import BaseModel, Field, PrivateAttr


class View(BaseModel):
    name: str
    rect: tuple[float, float, float, float]
    children: list["View"] = Field(default_factory=list)
    parent: "View" | None = Field(default=None)

    _anchors_in_subtree: list["Anchor"] = PrivateAttr(default_factory=list)

    # def anchor(self, type: str) -> "Anchor":
    #     return Anchor(view=self, type=type)

    def model_post_init(self, _):
        anchors = self.anchors()
        for child in self.children:
            child.parent = self
            child.model_post_init(_)
            anchors.extend(child._anchors_in_subtree)
        self._anchors_in_subtree = anchors

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
        "left", "right", "top", "bottom", "center_x", "center_y", "width", "height",
    ]

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
