from src.instantiation import template_instantiation
from src.learning import bayesian_learning
from src.pruning import HierarchicalPruner
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
    candidates = bayesian_learning(sketches, views, seed=42)
    selected = HierarchicalPruner(views)(candidates)
    actual_constraints = {repr(c) for c in selected}
    expected_constraints = {
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
    candidates = bayesian_learning(sketches, views, seed=42)
    selected = HierarchicalPruner(views)(candidates)
    actual_constraints = {repr(c) for c in selected}
    expected_constraints = {
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
    candidates = bayesian_learning(sketches, views, seed=42)
    selected = HierarchicalPruner(views)(candidates)
    actual_constraints = {repr(c) for c in selected}
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
    candidates = bayesian_learning(sketches, views, seed=42)
    selected = HierarchicalPruner(views)(candidates)
    actual_constraints = {repr(c) for c in selected}
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
    candidates = bayesian_learning(sketches, views, seed=42)
    selected = HierarchicalPruner(views)(candidates)
    actual_constraints = {repr(c) for c in selected}
    expected_constraints = {
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
    candidates = bayesian_learning(sketches, views, seed=42)
    selected = HierarchicalPruner(views)(candidates)
    actual_constraints = {repr(c) for c in selected}
    expected_constraints = {
        "LinearConstraint(child.height = 50)",
        "LinearConstraint(child.width = 50)",
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
    candidates = bayesian_learning(sketches, views, seed=42)
    selected = HierarchicalPruner(views)(candidates)
    actual_constraints = {repr(c) for c in selected}
    expected_constraints = {
        "LinearConstraint(bottom.height = 35)",
        "LinearConstraint(bottom.width = 80)",
        "LinearConstraint(top.height = 35)",
        "LinearConstraint(top.width = 80)",
        "LinearConstraint(bottom.center_x = 1 * top.center_x + 0)",
        "LinearConstraint(bottom.left = 1 * top.left + 0)",
        "LinearConstraint(bottom.right = 1 * top.right + 0)",
        "LinearConstraint(root.left = 1 * bottom.left + -10)",
        "LinearConstraint(root.left = 1 * top.left + -10)",
        "LinearConstraint(root.top = 1 * top.top + -10)",
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
    candidates = bayesian_learning(sketches, views, seed=42)
    selected = HierarchicalPruner(views)(candidates)
    actual_constraints = {repr(c) for c in selected}
    expected_constraints = {
        "LinearConstraint(left.height = 80)",
        "LinearConstraint(left.width = 35)",
        "LinearConstraint(right.height = 80)",
        "LinearConstraint(right.width = 35)",
        "LinearConstraint(left.bottom = 1 * right.bottom + 0)",
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
    candidates = bayesian_learning(sketches, views, seed=42)
    selected = HierarchicalPruner(views)(candidates)
    actual_constraints = {repr(c) for c in selected}
    expected_constraints = {
        "LinearConstraint(left.bottom = 1 * right.bottom + 0)",
        "LinearConstraint(left.center_y = 1 * right.center_y + 0)",
        "LinearConstraint(left.right = 1 * right.left + -10)",
        "LinearConstraint(left.top = 1 * right.top + 0)",
        "LinearConstraint(right.bottom = 1 * left.bottom + 0)",
        "LinearConstraint(right.center_y = 1 * left.center_y + 0)",
        "LinearConstraint(right.top = 1 * left.top + 0)",
        "LinearConstraint(root.bottom = 1 * left.bottom + 10)",
        "LinearConstraint(root.bottom = 1 * right.bottom + 10)",
        "LinearConstraint(root.center_y = 1 * left.center_y + 0)",
        "LinearConstraint(root.center_y = 1 * right.center_y + 0)",
        "LinearConstraint(root.left = 1 * left.left + -10)",
        "LinearConstraint(root.right = 1 * right.right + 10)",
        "LinearConstraint(root.top = 1 * left.top + -10)",
        "LinearConstraint(root.top = 1 * right.top + -10)",
    }
    assert actual_constraints == expected_constraints


def test_ieee_simple():
    """Test ieee-simple.json"""
    examples = [
        {
            "name": "root",
            "rect": [0, 0, 1200, 870],
            "children": [
                {"name": "topbar", "rect": [0, 0, 1200, 25]},
                {"name": "search", "rect": [0, 25, 1200, 435]},
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
                {"name": "topbar", "rect": [0, 0, 1600, 25]},
                {"name": "search", "rect": [0, 25, 1600, 435]},
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
    ]
    views = [View(**example) for example in examples]
    sketches = template_instantiation(views)
    candidates = bayesian_learning(sketches, views, seed=42)
    selected = HierarchicalPruner(views)(candidates)
    actual_constraints = {repr(c) for c in selected}
    expected_constraints = {
        "LinearConstraint(search.height = 410)",
        "LinearConstraint(root.center_x = 1 * topbar.center_x + 0)",
        "LinearConstraint(author1.center_y = 1 * author2.center_y + 0)",
        "LinearConstraint(root.width = 1 * topbar.width + 0)",
        "LinearConstraint(root.width = 1 * authors.width + 0)",
        "LinearConstraint(authors.left = 1 * search.left + 0)",
        "LinearConstraint(root.height = 87/41 * search.height + 0)",
        "LinearConstraint(root.height = 2 * authors.height + 0)",
        "LinearConstraint(topbar.right = 1 * search.right + 0)",
        "LinearConstraint(authors.bottom = 1 * author1.bottom + 30)",
        "LinearConstraint(author2.right = 1 * author3.left + -30)",
        "LinearConstraint(author1.height = 300)",
        "LinearConstraint(author3.top = 1 * author2.top + 0)",
        "LinearConstraint(author3.height = 300)",
        "LinearConstraint(search.left = 1 * topbar.left + 0)",
        "LinearConstraint(author2.bottom = 1 * author1.bottom + 0)",
        "LinearConstraint(root.right = 1 * authors.right + 0)",
        "LinearConstraint(topbar.left = 1 * search.left + 0)",
        "LinearConstraint(authors.top = 1 * author1.top + -105)",
        "LinearConstraint(search.left = 1 * authors.left + 0)",
        "LinearConstraint(author1.top = 1 * author2.top + 0)",
        "LinearConstraint(author2.height = 300)",
        "LinearConstraint(author2.center_y = 1 * author1.center_y + 0)",
        "LinearConstraint(search.center_x = 1 * authors.center_x + 0)",
        "LinearConstraint(author2.top = 1 * author3.top + 0)",
        "LinearConstraint(author2.center_y = 1 * author3.center_y + 0)",
        "LinearConstraint(topbar.height = 25)",
        "LinearConstraint(author1.right = 1 * author2.left + -30)",
        "LinearConstraint(authors.top = 1 * author3.top + -105)",
        "LinearConstraint(topbar.bottom = 1 * search.top + 0)",
        "LinearConstraint(author1.bottom = 1 * author2.bottom + 0)",
        "LinearConstraint(root.right = 1 * topbar.right + 0)",
        "LinearConstraint(authors.height = 29/20 * author3.height + 0)",
        "LinearConstraint(search.right = 1 * authors.right + 0)",
        "LinearConstraint(authors.bottom = 1 * author3.bottom + 30)",
        "LinearConstraint(author3.center_y = 1 * author2.center_y + 0)",
        "LinearConstraint(authors.bottom = 1 * author2.bottom + 30)",
        "LinearConstraint(authors.right = 1 * author3.right + 60)",
        "LinearConstraint(root.width = 1 * search.width + 0)",
        "LinearConstraint(root.center_x = 1 * authors.center_x + 0)",
        "LinearConstraint(authors.center_x = 1 * search.center_x + 0)",
        "LinearConstraint(search.bottom = 1 * authors.top + 0)",
        "LinearConstraint(root.left = 1 * search.left + 0)",
        "LinearConstraint(authors.height = 435)",
        "LinearConstraint(root.center_x = 1 * search.center_x + 0)",
        "LinearConstraint(authors.left = 1 * author1.left + -60)",
        "LinearConstraint(authors.top = 1 * author2.top + -105)",
        "LinearConstraint(author2.bottom = 1 * author3.bottom + 0)",
        "LinearConstraint(author2.top = 1 * author1.top + 0)",
        "LinearConstraint(root.top = 1 * topbar.top + 0)",
        "LinearConstraint(authors.height = 29/20 * author2.height + 0)",
        "LinearConstraint(search.right = 1 * topbar.right + 0)",
        "LinearConstraint(topbar.center_x = 1 * search.center_x + 0)",
        "LinearConstraint(author3.bottom = 1 * author2.bottom + 0)",
        "LinearConstraint(search.center_x = 1 * topbar.center_x + 0)",
        "LinearConstraint(root.right = 1 * search.right + 0)",
        "LinearConstraint(root.bottom = 1 * authors.bottom + 0)",
        "LinearConstraint(root.left = 1 * topbar.left + 0)",
        "LinearConstraint(authors.height = 29/20 * author1.height + 0)",
        "LinearConstraint(root.left = 1 * authors.left + 0)",
        "LinearConstraint(authors.right = 1 * search.right + 0)",
    }
    assert actual_constraints == expected_constraints
