from rich import print as rprint

from src.instantiation import template_instantiation
from src.learning import bayesian_learning
from src.pruning import HierarchicalPruner
from src.types import View

examples = [
    {
        "name": "root",
        "rect": [0, 0, 100, 100],
        "children": [
            {"name": "left", "rect": [10, 10, 45, 90]},
            {"name": "right", "rect": [55, 10, 90, 90]},
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 200, 100],
        "children": [
            {"name": "left", "rect": [10, 10, 95, 90]},
            {"name": "right", "rect": [105, 10, 190, 90]},
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 300, 100],
        "children": [
            {"name": "left", "rect": [10, 10, 145, 90]},
            {"name": "right", "rect": [155, 10, 290, 90]},
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 100, 200],
        "children": [
            {"name": "left", "rect": [10, 10, 45, 190]},
            {"name": "right", "rect": [55, 10, 90, 190]},
        ],
    },
]
views = [View(**example) for example in examples]
sketches = template_instantiation(views)
candidates = bayesian_learning(sketches, views, seed=42)

# Top candidates sorted by posterior score
for candidate in candidates:
    rprint(f"Score: {candidate.score:.3f} - {repr(candidate)}")
print("-" * 10)

# Hierarchical pruning (recommended)
pruner = HierarchicalPruner(views)
selected = pruner(candidates)

for candidate in selected:
    rprint(f"Score: {candidate.score:.3f} - {repr(candidate)}")
print("-" * 10)
