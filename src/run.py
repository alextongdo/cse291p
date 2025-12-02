from rich import print

from src.instantiation import conditional_template_instantiation
from src.learning import conditional_bayesian_learning
from src.logging import setup_logging
from src.pruning import conditional_hierarchical_pruning
from src.types import View

setup_logging(debug=False)

examples = [
    {
        "name": "root",
        "rect": [0, 0, 1200, 870],
        "children": [
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
    {
        "name": "root",
        "rect": [0, 0, 400, 1470],
        "children": [
            {
                "name": "authors",
                "rect": [0, 510, 400, 1470],
                "children": [
                    {"name": "author1", "rect": [10, 525, 390, 825]},
                    {"name": "author2", "rect": [10, 840, 390, 1140]},
                    {"name": "author3", "rect": [10, 1155, 390, 1455]},
                ],
            },
        ],
    },
]

views = [View(**example) for example in examples]
example_idxs_to_templates_map = conditional_template_instantiation(views)
# print(repr(example_idxs_to_templates_map))
print({ind: len(lst) for ind, lst in example_idxs_to_templates_map.items()})
example_idxs_to_constrs_map = conditional_bayesian_learning(
    example_idxs_to_templates_map, views, seed=42
)
# print(repr(example_idxs_to_constrs_map))
print({ind: len(lst) for ind, lst in example_idxs_to_constrs_map.items()})

outputs = conditional_hierarchical_pruning(example_idxs_to_constrs_map, views)

print(repr(outputs))
