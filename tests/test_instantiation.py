from src.instantiation import template_instantiation
from src.types import View


def test_1x1_fixed_centered():
    """Test 1x1_fixed-ltr_centered-x_aspectratio-4-3.json"""
    examples = [
        {
            "name": "root",
            "rect": [0, 0, 100, 200],
            "children": [{"name": "child", "rect": [30, 10, 70, 40]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 200, 200],
            "children": [{"name": "child", "rect": [30, 10, 170, 115]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 300, 200],
            "children": [{"name": "child", "rect": [30, 10, 270, 190]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 100, 400],
            "children": [{"name": "child", "rect": [30, 10, 70, 40]}],
        },
    ]
    sketches = template_instantiation([View(**example) for example in examples])

    actual_constraints = {repr(s) for s in sketches}

    expected_constraints = {
        "LinearConstraint(child.width = a * child.height + 0.0)",
        "LinearConstraint(root.width = a * root.height + 0.0)",
        "LinearConstraint(root.height = a * child.height + 0.0)",
        "LinearConstraint(root.width = a * child.width + 0.0)",
        "LinearConstraint(child.height = b)",
        "LinearConstraint(child.width = b)",
        "LinearConstraint(root.height = b)",
        "LinearConstraint(root.width = b)",
        "LinearConstraint(root.bottom = 1.0 * child.bottom + b)",
        "LinearConstraint(root.center_x = 1.0 * child.center_x + b)",
        "LinearConstraint(root.center_y = 1.0 * child.center_y + b)",
        "LinearConstraint(root.left = 1.0 * child.left + b)",
        "LinearConstraint(root.right = 1.0 * child.right + b)",
        "LinearConstraint(root.top = 1.0 * child.top + b)",
    }

    # Compare
    print("\n=== Actual Constraints ===")
    for c in sorted(actual_constraints):
        print(f"  {c}")

    print("\n=== Expected Constraints ===")
    for c in sorted(expected_constraints):
        print(f"  {c}")

    print("\n=== Missing from Actual ===")
    missing = expected_constraints - actual_constraints
    for c in sorted(missing):
        print(f"  {c}")

    print("\n=== Extra in Actual ===")
    extra = actual_constraints - expected_constraints
    for c in sorted(extra):
        print(f"  {c}")

    assert actual_constraints == expected_constraints


if __name__ == "__main__":
    test_1x1_fixed_centered()
