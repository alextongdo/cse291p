from rich import print as rprint

from src.instantiation import template_instantiation
from src.types import View

examples = [
    {
        "name": "root",
        "rect": [0, 0, 100, 100],
        "children": [
            {"name": "top", "rect": [10, 10, 90, 45]},
            {"name": "bottom", "rect": [10, 55, 90, 90]},
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 200, 100],
        "children": [
            {"name": "top", "rect": [10, 10, 90, 45]},
            {"name": "bottom", "rect": [10, 55, 90, 90]},
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 300, 100],
        "children": [
            {"name": "top", "rect": [10, 10, 90, 45]},
            {"name": "bottom", "rect": [10, 55, 90, 90]},
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 100, 200],
        "children": [
            {"name": "top", "rect": [10, 10, 90, 45]},
            {"name": "bottom", "rect": [10, 55, 90, 90]},
        ],
    },
]

sketches = template_instantiation([View(**example) for example in examples])
for s in sketches:
    rprint(repr(s))
