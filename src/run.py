from rich import print as rprint

from src.learning import BayesianLearning
from src.instantiation import template_instantiation
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
            {"name": "left", "rect": [10, 10, 45, 90]},
            {"name": "right", "rect": [55, 10, 90, 90]},
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 300, 100],
        "children": [
            {"name": "left", "rect": [10, 10, 45, 90]},
            {"name": "right", "rect": [55, 10, 90, 90]},
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 100, 200],
        "children": [
            {"name": "left", "rect": [10, 10, 45, 90]},
            {"name": "right", "rect": [55, 10, 90, 90]},
        ],
    },
]
examples = [View(**example) for example in examples]
sketches = template_instantiation(examples)
for s in sketches:
    rprint(repr(s))

learner = BayesianLearning(sketches, examples)
candidates = learner.learn_flat()

# Top candidates sorted by posterior score
for candidate in candidates:
    if candidate.score > 0.1:
        rprint(f"Score: {candidate.score:.3f} - {repr(candidate.constraint)}")
