from rich import rprint

from src.types import View

bruh = {
    "name": "root",
    "rect": [0, 0, 1200, 800],
    "children": [
        {"name": "header", "rect": [0, 0, 1200, 80], "children": []},
        {"name": "sidebar", "rect": [0, 80, 250, 800], "children": []},
        {"name": "main", "rect": [250, 80, 1200, 800], "children": []},
    ],
}

lol = View(**bruh)
rprint(lol)
rprint(lol._anchors_in_subtree)
