from rich import print as rprint

from src.instantiation import template_instantiation
from src.types import View

example = {
    "name": "root",
    "rect": [0, 0, 1200, 800],
    "children": [
        {"name": "header", "rect": [0, 0, 1200, 80], "children": []},
        {"name": "sidebar", "rect": [0, 80, 250, 800], "children": []},
        {"name": "main", "rect": [250, 80, 1200, 800], "children": []},
    ],
}

root = View(**example)
sketches = template_instantiation(root)
rprint(repr(sketches))
