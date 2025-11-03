from src.instantiation import template_instantiation
from src.types import View


def test_single_view():
    example = {
        "name": "root",
        "rect": [0, 0, 800, 600],
        "children": [],
    }
    root = View(**example)
    sketches = template_instantiation(root)

    # TODO: Add assertions after running against original mockdown
    # Expected number of sketches
    # assert len(sketches) == ???

    # Count by constraint type
    aspect_ratio_constraints = [  # noqa: F841
        s for s in sketches if s.x is not None and s.a is None and s.b == 0.0
    ]
    constant_constraints = [  # noqa: F841
        s for s in sketches if s.x is None and s.a == 0.0 and s.b is None
    ]

    # TODO: Add assertions
    # assert len(aspect_ratio_constraints) == ???
    # assert len(constant_constraints) == ???

    # Check specific constraints exist
    # Example: root.width = a * root.height
    # width_height_constraint = next(
    #     (s for s in sketches
    #      if s.y.view.name == "root" and s.y.type == "width"
    #      and s.x and s.x.view.name == "root" and s.x.type == "height"),
    #     None
    # )
    # assert width_height_constraint is not None
    # assert width_height_constraint.a is None
    # assert width_height_constraint.b == 0.0
