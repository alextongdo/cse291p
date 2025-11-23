from rich import print as rprint

from src.instantiation import template_instantiation
from src.learning import bayesian_learning
from src.pruning import HierarchicalPruner
from src.render import visualize
from src.types import View
from src.logging import setup_logging

setup_logging(debug=True)

examples = [
    {
        "name": "root",
        "rect": [0, 0, 1200, 870],
        "children": [
            # {"name": "topbar", "rect": [0, 0, 1200, 25]},
            # {"name": "search", "rect": [0, 25, 1200, 435]},
            {
                "name": "authors",
                "rect": [0, 435, 1200, 870],
                "children": [
                    {"name": "author1", "rect": [60, 540, 400, 840]},
                    {"name": "author2", "rect": [430, 540, 770, 840]},
                    {"name": "author3", "rect": [800, 540, 1140, 840]},
                ],
            },
        ],
    },
    # {
    #     "name": "root",
    #     "rect": [0, 0, 1600, 870],
    #     "children": [
    #         {"name": "topbar", "rect": [0, 0, 1600, 25]},
    #         {"name": "search", "rect": [0, 25, 1600, 435]},
    #         {
    #             "name": "authors",
    #             "rect": [0, 435, 1600, 870],
    #             "children": [
    #                 {"name": "author1", "rect": [60, 540, 533.33, 840]},
    #                 {"name": "author2", "rect": [563.33, 540, 1036.66, 840]},
    #                 {"name": "author3", "rect": [1066.66, 540, 1539.99, 840]},
    #             ],
    #         },
    #     ],
    # },
    {
        "name": "root",
        "rect": [0, 0, 500, 1530],
        "children": [
            # {"name": "topbar", "rect": [0, 0, 500, 25]},
            # {"name": "search", "rect": [0, 25, 500, 510]},
            {
                "name": "authors",
                "rect": [0, 510, 500, 1530],
                "children": [
                    {"name": "author1", "rect": [60, 540, 440, 840]},
                    {"name": "author2", "rect": [60, 870, 440, 1170]},
                    {"name": "author3", "rect": [60, 1200, 440, 1500]},
                ],
            },
        ],
    },
    # {
    #     "name": "root",
    #     "rect": [0, 0, 400, 1470],
    #     "children": [
    #         {"name": "topbar", "rect": [0, 0, 400, 25]},
    #         {"name": "search", "rect": [0, 25, 400, 510]},
    #         {
    #             "name": "authors",
    #             "rect": [0, 510, 400, 1470],
    #             "children": [
    #                 {"name": "author1", "rect": [10, 525, 390, 825]},
    #                 {"name": "author2", "rect": [10, 840, 390, 1140]},
    #                 {"name": "author3", "rect": [10, 1155, 390, 1455]},
    #             ],
    #         },
    #     ],
    # },
]
views = [View(**example) for example in examples]
sketches = template_instantiation(views)
candidates = bayesian_learning(sketches, views, seed=42)
pruner = HierarchicalPruner(views)
selected = pruner(candidates)

for candidate in selected:
    rprint(f"Score: {candidate.score:.3f} - {repr(candidate)}")

# visualize(
#     views[0],
#     selected,
#     width=500,
#     height=870,
# )
