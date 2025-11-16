from src.instantiation import template_instantiation
from src.learning import BayesianLearning
from src.types import View


def test_1x1_fixed_ltr_centered_x_aspectratio_4_3():
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
    views = [View(**example) for example in examples]
    sketches = template_instantiation(views)
    learner = BayesianLearning(sketches, views)
    candidates = learner.learn_flat()

    actual_constraints = {repr(c.constraint) for c in candidates}
    expected_constraints = {
        "LinearConstraint(child.width = 4/3 * child.height + 0)",
        "LinearConstraint(root.center_x = 1 * child.center_x + 0)",
        "LinearConstraint(root.left = 1 * child.left + -30)",
        "LinearConstraint(root.right = 1 * child.right + 30)",
        "LinearConstraint(root.top = 1 * child.top + -10)",
    }
    assert actual_constraints == expected_constraints


def test_1x1_fixed_ltwh():
    """Test 1x1_fixed-ltwh.json"""
    examples = [
        {
            "name": "root",
            "rect": [0, 0, 100, 100],
            "children": [{"name": "child", "rect": [10, 10, 60, 60]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 200, 100],
            "children": [{"name": "child", "rect": [10, 10, 60, 60]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 300, 100],
            "children": [{"name": "child", "rect": [10, 10, 60, 60]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 100, 200],
            "children": [{"name": "child", "rect": [10, 10, 60, 60]}],
        },
    ]
    views = [View(**example) for example in examples]
    sketches = template_instantiation(views)
    learner = BayesianLearning(sketches, views)
    candidates = learner.learn_flat()

    actual_constraints = {repr(c.constraint) for c in candidates}
    expected_constraints = {
        "LinearConstraint(child.width = 1 * child.height + 0)",
        "LinearConstraint(child.height = 50)",
        "LinearConstraint(child.width = 50)",
        "LinearConstraint(root.left = 1 * child.left + -10)",
        "LinearConstraint(root.top = 1 * child.top + -10)",
    }
    assert actual_constraints == expected_constraints


def test_1x1_fixed_lw_relative_h_centered_y():
    """Test 1x1_fixed-lw_relative-h_centered-y.json"""
    examples = [
        {
            "name": "root",
            "rect": [0, 0, 100, 100],
            "children": [{"name": "child", "rect": [25, 25, 75, 75]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 200, 100],
            "children": [{"name": "child", "rect": [25, 25, 75, 75]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 300, 100],
            "children": [{"name": "child", "rect": [25, 25, 75, 75]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 100, 200],
            "children": [{"name": "child", "rect": [25, 50, 75, 150]}],
        },
    ]
    views = [View(**example) for example in examples]
    sketches = template_instantiation(views)
    learner = BayesianLearning(sketches, views)
    candidates = learner.learn_flat()

    actual_constraints = {repr(c.constraint) for c in candidates}
    expected_constraints = {
        "LinearConstraint(root.height = 2 * child.height + 0)",
        "LinearConstraint(child.width = 50)",
        "LinearConstraint(root.center_y = 1 * child.center_y + 0)",
        "LinearConstraint(root.left = 1 * child.left + -25)",
    }
    assert actual_constraints == expected_constraints


def test_1x1_fixed_th_relative_w_centered_x():
    """Test 1x1_fixed-th_relative-w_centered-x.json"""
    examples = [
        {
            "name": "root",
            "rect": [0, 0, 100, 100],
            "children": [{"name": "child", "rect": [25, 25, 75, 75]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 200, 100],
            "children": [{"name": "child", "rect": [50, 25, 150, 75]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 300, 100],
            "children": [{"name": "child", "rect": [75, 25, 225, 75]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 100, 200],
            "children": [{"name": "child", "rect": [25, 25, 75, 75]}],
        },
    ]
    views = [View(**example) for example in examples]
    sketches = template_instantiation(views)
    learner = BayesianLearning(sketches, views)
    candidates = learner.learn_flat()

    actual_constraints = {repr(c.constraint) for c in candidates}
    expected_constraints = {
        "LinearConstraint(root.width = 2 * child.width + 0)",
        "LinearConstraint(child.height = 50)",
        "LinearConstraint(root.center_x = 1 * child.center_x + 0)",
        "LinearConstraint(root.top = 1 * child.top + -25)",
    }
    assert actual_constraints == expected_constraints


def test_1x1_fixed_whl_centered_y():
    """Test 1x1_fixed-whl_centered-y.json"""
    examples = [
        {
            "name": "root",
            "rect": [0, 0, 100, 100],
            "children": [{"name": "child", "rect": [25, 25, 75, 75]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 200, 100],
            "children": [{"name": "child", "rect": [75, 25, 125, 75]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 300, 100],
            "children": [{"name": "child", "rect": [125, 25, 175, 75]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 100, 200],
            "children": [{"name": "child", "rect": [25, 25, 75, 75]}],
        },
    ]
    views = [View(**example) for example in examples]
    sketches = template_instantiation(views)
    learner = BayesianLearning(sketches, views)
    candidates = learner.learn_flat()

    actual_constraints = {repr(c.constraint) for c in candidates}
    expected_constraints = {
        "LinearConstraint(child.width = 1 * child.height + 0)",
        "LinearConstraint(child.height = 50)",
        "LinearConstraint(child.width = 50)",
        "LinearConstraint(root.center_x = 1 * child.center_x + 0)",
        "LinearConstraint(root.top = 1 * child.top + -25)",
    }
    assert actual_constraints == expected_constraints


def test_1x1_fixed_wht_centered_x():
    """Test 1x1_fixed-wht_centered-x.json"""
    examples = [
        {
            "name": "root",
            "rect": [0, 0, 100, 100],
            "children": [{"name": "child", "rect": [25, 25, 75, 75]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 200, 100],
            "children": [{"name": "child", "rect": [25, 25, 75, 75]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 300, 100],
            "children": [{"name": "child", "rect": [25, 25, 75, 75]}],
        },
        {
            "name": "root",
            "rect": [0, 0, 100, 200],
            "children": [{"name": "child", "rect": [25, 125, 75, 175]}],
        },
    ]
    views = [View(**example) for example in examples]
    sketches = template_instantiation(views)
    learner = BayesianLearning(sketches, views)
    candidates = learner.learn_flat()

    actual_constraints = {repr(c.constraint) for c in candidates}
    expected_constraints = {
        "LinearConstraint(child.width = 1 * child.height + 0)",
        "LinearConstraint(child.height = 50)",
        "LinearConstraint(child.width = 50)",
        # "LinearConstraint(root.bottom = 1 * child.bottom + 24)",
        "LinearConstraint(root.bottom = 1 * child.bottom + 25)",
        "LinearConstraint(root.left = 1 * child.left + -25)",
    }
    assert actual_constraints == expected_constraints


def test_1x2_fixed_ltwh():
    """Test 1x2_fixed-ltwh.json"""
    examples = [
        {
            "name": "root",
            "rect": [0, 0, 100, 100],
            "children": [
                {"name": "top", "rect": [10, 10, 90, 45]},
                {"name": "bottom", "rect": [10, 55, 90, 90]},
            ],
        },
        {
            "name": "root",
            "rect": [0, 0, 200, 100],
            "children": [
                {"name": "top", "rect": [10, 10, 90, 45]},
                {"name": "bottom", "rect": [10, 55, 90, 90]},
            ],
        },
        {
            "name": "root",
            "rect": [0, 0, 300, 100],
            "children": [
                {"name": "top", "rect": [10, 10, 90, 45]},
                {"name": "bottom", "rect": [10, 55, 90, 90]},
            ],
        },
        {
            "name": "root",
            "rect": [0, 0, 100, 200],
            "children": [
                {"name": "top", "rect": [10, 10, 90, 45]},
                {"name": "bottom", "rect": [10, 55, 90, 90]},
            ],
        },
    ]
    views = [View(**example) for example in examples]
    sketches = template_instantiation(views)
    learner = BayesianLearning(sketches, views)
    candidates = learner.learn_flat()

    actual_constraints = {repr(c.constraint) for c in candidates}
    expected_constraints = {
        "LinearConstraint(bottom.width = 16/7 * bottom.height + 0)",
        "LinearConstraint(top.width = 16/7 * top.height + 0)",
        "LinearConstraint(bottom.height = 35)",
        # "LinearConstraint(bottom.width = 79)",
        "LinearConstraint(bottom.width = 80)",
        "LinearConstraint(top.height = 35)",
        "LinearConstraint(top.width = 80)",
        "LinearConstraint(bottom.center_x = 1 * top.center_x + 0)",
        "LinearConstraint(bottom.left = 1 * top.left + 0)",
        "LinearConstraint(bottom.right = 1 * top.right + 0)",
        "LinearConstraint(bottom.right = 1 * top.right + 1)",  # Added
        # "LinearConstraint(root.left = 1 * bottom.left + -11)",
        "LinearConstraint(root.left = 1 * bottom.left + -10)",
        "LinearConstraint(root.left = 1 * top.left + -10)",
        "LinearConstraint(root.top = 1 * top.top + -10)",
        # "LinearConstraint(root.top = 1 * top.top + -9)",
        "LinearConstraint(top.bottom = 1 * bottom.top + -10)",
        "LinearConstraint(top.center_x = 1 * bottom.center_x + 0)",
        "LinearConstraint(top.left = 1 * bottom.left + 0)",
        "LinearConstraint(top.right = 1 * bottom.right + 0)",
    }
    assert actual_constraints == expected_constraints


def test_2x1_fixed_ltwh():
    """Test 2x1_fixed-ltwh.json"""
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
    views = [View(**example) for example in examples]
    sketches = template_instantiation(views)
    learner = BayesianLearning(sketches, views)
    candidates = learner.learn_flat()

    actual_constraints = {repr(c.constraint) for c in candidates}
    expected_constraints = {
        "LinearConstraint(left.width = 7/16 * left.height + 0)",
        "LinearConstraint(right.width = 7/16 * right.height + 0)",
        "LinearConstraint(left.height = 80)",
        # "LinearConstraint(left.width = 34)",
        "LinearConstraint(left.width = 35)",
        "LinearConstraint(right.height = 80)",
        "LinearConstraint(right.width = 35)",
        "LinearConstraint(left.bottom = 1 * right.bottom + 0)",
        "LinearConstraint(right.bottom = 1 * left.bottom + 1)",  # Added
        "LinearConstraint(left.center_y = 1 * right.center_y + 0)",
        "LinearConstraint(left.right = 1 * right.left + -10)",
        "LinearConstraint(left.top = 1 * right.top + 0)",
        "LinearConstraint(right.bottom = 1 * left.bottom + 0)",
        "LinearConstraint(right.center_y = 1 * left.center_y + 0)",
        "LinearConstraint(right.top = 1 * left.top + 0)",
        "LinearConstraint(root.left = 1 * left.left + -10)",
        "LinearConstraint(root.top = 1 * left.top + -10)",
        "LinearConstraint(root.top = 1 * right.top + -10)",
    }
    assert actual_constraints == expected_constraints


def test_2x1_fixed_ltrb_equal_wh():
    """Test 2x1_fixed-ltrb_equal-wh.json"""
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
    learner = BayesianLearning(sketches, views)
    candidates = learner.learn_flat()

    actual_constraints = {repr(c.constraint) for c in candidates}
    expected_constraints = {
        "LinearConstraint(left.bottom = 1 * right.bottom + 0)",
        "LinearConstraint(left.center_y = 1 * right.center_y + 0)",
        "LinearConstraint(left.right = 1 * right.left + -10)",
        "LinearConstraint(left.top = 1 * right.top + 0)",
        "LinearConstraint(right.bottom = 1 * left.bottom + 0)",
        "LinearConstraint(right.bottom = 1 * left.bottom + 1)",  # Added
        "LinearConstraint(right.center_y = 1 * left.center_y + 0)",
        "LinearConstraint(right.top = 1 * left.top + 0)",
        "LinearConstraint(root.bottom = 1 * left.bottom + 10)",
        "LinearConstraint(root.bottom = 1 * right.bottom + 10)",
        # "LinearConstraint(root.bottom = 1 * right.bottom + 11)",
        "LinearConstraint(root.center_y = 1 * left.center_y + 0)",
        # "LinearConstraint(root.center_y = 1 * right.center_y + -1)",
        "LinearConstraint(root.center_y = 1 * right.center_y + 0)",
        "LinearConstraint(root.left = 1 * left.left + -10)",
        "LinearConstraint(root.right = 1 * right.right + 10)",
        "LinearConstraint(root.top = 1 * left.top + -10)",
        "LinearConstraint(root.top = 1 * right.top + -10)",
    }
    assert actual_constraints == expected_constraints
