from src.main import ConditionalMockdown
from src.types import View
from src.visualize import visualize

# def load_json(filename: str):
#     path = Path(__file__).parent / filename
#     with open(path) as f:
#         return json.load(f)

# data = load_json("data/ieee-simple.json")
# examples = data["examples"]

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
    {
        "name": "root",
        "rect": [0, 0, 1600, 870],
        "children": [
            {
                "name": "authors",
                "rect": [0, 435, 1600, 870],
                "children": [
                    {"name": "author1", "rect": [60, 540, 533.33, 840]},
                    {"name": "author2", "rect": [563.33, 540, 1036.66, 840]},
                    {"name": "author3", "rect": [1066.66, 540, 1539.99, 840]},
                ],
            },
        ],
    },
    # {
    #     "name": "root",
    #     "rect": [0, 0, 500, 1530],
    #     "children": [
    #         {
    #             "name": "authors",
    #             "rect": [0, 510, 500, 1530],
    #             "children": [
    #                 {"name": "author1", "rect": [10, 540, 440, 840]},
    #                 {"name": "author2", "rect": [10, 870, 440, 1170]},
    #                 {"name": "author3", "rect": [10, 1200, 440, 1500]},
    #             ],
    #         },
    #     ],
    # },
    # {
    #     "name": "root",
    #     "rect": [0, 0, 400, 1470],
    #     "children": [
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
mockdown = ConditionalMockdown()
mockdown.fit(views)
rects = mockdown.predict(width=views[-1].width + 10, height=views[-1].height)
visualize(rects, root_name="root")
