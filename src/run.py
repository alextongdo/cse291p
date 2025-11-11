from rich import print as rprint

from src.instantiation import template_instantiation
from src.types import View

examples = [
    {
      "name": "root",
      "rect": [0, 0, 100, 200],
      "children": [
        {
          "name": "child",
          "rect": [30, 10, 70, 40]
        }
      ]
    },
    {
      "name": "root",
      "rect": [0, 0, 200, 200],
      "children": [
        {
          "name": "child",
          "rect": [30, 10, 170, 115]
        }
      ]
    },
    {
      "name": "root",
      "rect": [0, 0, 300, 200],
      "children": [
        {
          "name": "child",
          "rect": [30, 10, 270, 190]
        }
      ]
    },
    {
      "name": "root",
      "rect": [0, 0, 100, 400],
      "children": [
        {
          "name": "child",
          "rect": [30, 10, 70, 40]
        }
      ]
    }
  ]

sketches = template_instantiation([View(**example) for example in examples])
for s in sketches:
  rprint(repr(s))
