from src.main import ConditionalMockdown, Mockdown
from src.types import View
from src.visualize import visualize

examples = [
    {
        "name": "root",
        "rect": [0, 0, 1440, 1000],
        "_viewport": {
            "width": 1440,
            "height": 1000,
            "label": "Desktop Large",
            "category": "desktop",
        },
        "children": [
            {"name": "header", "rect": [0, 0, 1440, 80]},
            {
                "name": "content",
                "rect": [0, 80, 1440, 1000],
                "children": [
                    {"name": "col_left", "rect": [0, 80, 360, 1000]},
                    {
                        "name": "col_hero",
                        "rect": [360, 80, 1080, 1000],
                        "children": [
                            {"name": "hero_img", "rect": [360, 80, 1080, 586]},
                            {"name": "hero_text", "rect": [360, 586, 1080, 954]},
                        ],
                    },
                    {"name": "col_right", "rect": [1080, 80, 1440, 1000]},
                ],
            },
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 1280, 900],
        "_viewport": {
            "width": 1280,
            "height": 900,
            "label": "Desktop Standard",
            "category": "desktop",
        },
        "children": [
            {"name": "header", "rect": [0, 0, 1280, 72]},
            {
                "name": "content",
                "rect": [0, 72, 1280, 900],
                "children": [
                    {"name": "col_left", "rect": [0, 72, 320, 900]},
                    {
                        "name": "col_hero",
                        "rect": [320, 72, 960, 900],
                        "children": [
                            {"name": "hero_img", "rect": [320, 72, 960, 529]},
                            {"name": "hero_text", "rect": [320, 529, 960, 860]},
                        ],
                    },
                    {"name": "col_right", "rect": [960, 72, 1280, 900]},
                ],
            },
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 1024, 800],
        "_viewport": {
            "width": 1024,
            "height": 800,
            "label": "Tablet Landscape",
            "category": "tablet",
        },
        "children": [
            {"name": "header", "rect": [0, 0, 1024, 64]},
            {
                "name": "content",
                "rect": [0, 64, 1024, 800],
                "children": [
                    {"name": "col_left", "rect": [0, 64, 256, 800]},
                    {
                        "name": "col_hero",
                        "rect": [256, 64, 768, 800],
                        "children": [
                            {"name": "hero_img", "rect": [256, 64, 768, 469]},
                            {"name": "hero_text", "rect": [256, 469, 768, 744]},
                        ],
                    },
                    {"name": "col_right", "rect": [768, 64, 1024, 800]},
                ],
            },
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 360, 762],
        "_viewport": {
            "width": 360,
            "height": 762,
            "label": "Mobile Large",
            "category": "mobile",
        },
        "children": [
            {"name": "header", "rect": [0, 0, 360, 60]},
            {
                "name": "content",
                "rect": [0, 60, 360, 762],
                "children": [
                    {
                        "name": "col_hero",
                        "rect": [0, 60, 360, 501.6],
                        "children": [
                            {"name": "hero_img", "rect": [0, 60, 360, 300.96]},
                            {"name": "hero_text", "rect": [0, 300.96, 360, 501.6]},
                        ],
                    },
                    {"name": "col_left", "rect": [0, 501.6, 360, 632.88]},
                    {"name": "col_right", "rect": [0, 632.88, 360, 762]},
                ],
            },
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 360, 760],
        "_viewport": {
            "width": 360,
            "height": 760,
            "label": "Mobile Medium",
            "category": "mobile",
        },
        "children": [
            {"name": "header", "rect": [0, 0, 360, 60]},
            {
                "name": "content",
                "rect": [0, 60, 360, 760],
                "children": [
                    {
                        "name": "col_hero",
                        "rect": [0, 60, 360, 480],
                        "children": [
                            {"name": "hero_img", "rect": [0, 60, 360, 300]},
                            {"name": "hero_text", "rect": [0, 300, 360, 480]},
                        ],
                    },
                    {"name": "col_left", "rect": [0, 480, 360, 630]},
                    {"name": "col_right", "rect": [0, 630, 360, 760]},
                ],
            },
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 360, 758],
        "_viewport": {
            "width": 360,
            "height": 758,
            "label": "Mobile Small",
            "category": "mobile",
        },
        "children": [
            {"name": "header", "rect": [0, 0, 360, 60]},
            {
                "name": "content",
                "rect": [0, 60, 360, 758],
                "children": [
                    {
                        "name": "col_hero",
                        "rect": [0, 60, 360, 478.08],
                        "children": [
                            {"name": "hero_img", "rect": [0, 60, 360, 297.6]},
                            {"name": "hero_text", "rect": [0, 297.6, 360, 478.08]},
                        ],
                    },
                    {"name": "col_left", "rect": [0, 478.08, 360, 618.24]},
                    {"name": "col_right", "rect": [0, 618.24, 360, 758]},
                ],
            },
        ],
    },
]

views = [View(**example) for example in examples]
mockdown = ConditionalMockdown()
# mockdown = Mockdown()
mockdown.fit(views)
rects = mockdown.predict(width=views[-1].width, height=views[-1].height)
visualize(rects, root_name=views[0].name)
