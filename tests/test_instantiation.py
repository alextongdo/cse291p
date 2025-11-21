from src.instantiation import template_instantiation
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
    sketches = template_instantiation([View(**example) for example in examples])
    actual_constraints = {repr(s) for s in sketches}
    expected_constraints = {
        "LinearConstraint(child.width = a * child.height + 0)",
        "LinearConstraint(root.width = a * root.height + 0)",
        "LinearConstraint(root.height = a * child.height + 0)",
        "LinearConstraint(root.width = a * child.width + 0)",
        "LinearConstraint(child.height = b)",
        "LinearConstraint(child.width = b)",
        "LinearConstraint(root.height = b)",
        "LinearConstraint(root.width = b)",
        "LinearConstraint(root.bottom = 1 * child.bottom + b)",
        "LinearConstraint(root.center_x = 1 * child.center_x + b)",
        "LinearConstraint(root.center_y = 1 * child.center_y + b)",
        "LinearConstraint(root.left = 1 * child.left + b)",
        "LinearConstraint(root.right = 1 * child.right + b)",
        "LinearConstraint(root.top = 1 * child.top + b)",
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
    sketches = template_instantiation([View(**example) for example in examples])
    actual_constraints = {repr(s) for s in sketches}
    expected_constraints = {
        "LinearConstraint(child.width = a * child.height + 0)",
        "LinearConstraint(root.width = a * root.height + 0)",
        "LinearConstraint(root.height = a * child.height + 0)",
        "LinearConstraint(root.width = a * child.width + 0)",
        "LinearConstraint(child.height = b)",
        "LinearConstraint(child.width = b)",
        "LinearConstraint(root.height = b)",
        "LinearConstraint(root.width = b)",
        "LinearConstraint(root.bottom = 1 * child.bottom + b)",
        "LinearConstraint(root.center_x = 1 * child.center_x + b)",
        "LinearConstraint(root.center_y = 1 * child.center_y + b)",
        "LinearConstraint(root.left = 1 * child.left + b)",
        "LinearConstraint(root.right = 1 * child.right + b)",
        "LinearConstraint(root.top = 1 * child.top + b)",
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
    sketches = template_instantiation([View(**example) for example in examples])
    actual_constraints = {repr(s) for s in sketches}
    expected_constraints = {
        "LinearConstraint(child.width = a * child.height + 0)",
        "LinearConstraint(root.width = a * root.height + 0)",
        "LinearConstraint(root.height = a * child.height + 0)",
        "LinearConstraint(root.width = a * child.width + 0)",
        "LinearConstraint(child.height = b)",
        "LinearConstraint(child.width = b)",
        "LinearConstraint(root.height = b)",
        "LinearConstraint(root.width = b)",
        "LinearConstraint(root.bottom = 1 * child.bottom + b)",
        "LinearConstraint(root.center_x = 1 * child.center_x + b)",
        "LinearConstraint(root.center_y = 1 * child.center_y + b)",
        "LinearConstraint(root.left = 1 * child.left + b)",
        "LinearConstraint(root.right = 1 * child.right + b)",
        "LinearConstraint(root.top = 1 * child.top + b)",
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
    sketches = template_instantiation([View(**example) for example in examples])
    actual_constraints = {repr(s) for s in sketches}
    expected_constraints = {
        "LinearConstraint(child.width = a * child.height + 0)",
        "LinearConstraint(root.width = a * root.height + 0)",
        "LinearConstraint(root.height = a * child.height + 0)",
        "LinearConstraint(root.width = a * child.width + 0)",
        "LinearConstraint(child.height = b)",
        "LinearConstraint(child.width = b)",
        "LinearConstraint(root.height = b)",
        "LinearConstraint(root.width = b)",
        "LinearConstraint(root.bottom = 1 * child.bottom + b)",
        "LinearConstraint(root.center_x = 1 * child.center_x + b)",
        "LinearConstraint(root.center_y = 1 * child.center_y + b)",
        "LinearConstraint(root.left = 1 * child.left + b)",
        "LinearConstraint(root.right = 1 * child.right + b)",
        "LinearConstraint(root.top = 1 * child.top + b)",
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
    sketches = template_instantiation([View(**example) for example in examples])
    actual_constraints = {repr(s) for s in sketches}
    expected_constraints = {
        "LinearConstraint(child.width = a * child.height + 0)",
        "LinearConstraint(root.width = a * root.height + 0)",
        "LinearConstraint(root.height = a * child.height + 0)",
        "LinearConstraint(root.width = a * child.width + 0)",
        "LinearConstraint(child.height = b)",
        "LinearConstraint(child.width = b)",
        "LinearConstraint(root.height = b)",
        "LinearConstraint(root.width = b)",
        "LinearConstraint(root.bottom = 1 * child.bottom + b)",
        "LinearConstraint(root.center_x = 1 * child.center_x + b)",
        "LinearConstraint(root.center_y = 1 * child.center_y + b)",
        "LinearConstraint(root.left = 1 * child.left + b)",
        "LinearConstraint(root.right = 1 * child.right + b)",
        "LinearConstraint(root.top = 1 * child.top + b)",
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
    sketches = template_instantiation([View(**example) for example in examples])
    actual_constraints = {repr(s) for s in sketches}
    expected_constraints = {
        "LinearConstraint(child.width = a * child.height + 0)",
        "LinearConstraint(root.width = a * root.height + 0)",
        "LinearConstraint(root.height = a * child.height + 0)",
        "LinearConstraint(root.width = a * child.width + 0)",
        "LinearConstraint(child.height = b)",
        "LinearConstraint(child.width = b)",
        "LinearConstraint(root.height = b)",
        "LinearConstraint(root.width = b)",
        "LinearConstraint(root.bottom = 1 * child.bottom + b)",
        "LinearConstraint(root.center_x = 1 * child.center_x + b)",
        "LinearConstraint(root.center_y = 1 * child.center_y + b)",
        "LinearConstraint(root.left = 1 * child.left + b)",
        "LinearConstraint(root.right = 1 * child.right + b)",
        "LinearConstraint(root.top = 1 * child.top + b)",
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
    sketches = template_instantiation([View(**example) for example in examples])
    actual_constraints = {repr(s) for s in sketches}
    expected_constraints = {
        "LinearConstraint(bottom.width = a * bottom.height + 0)",
        "LinearConstraint(root.width = a * root.height + 0)",
        "LinearConstraint(top.width = a * top.height + 0)",
        "LinearConstraint(root.height = a * bottom.height + 0)",
        "LinearConstraint(root.height = a * top.height + 0)",
        "LinearConstraint(root.width = a * bottom.width + 0)",
        "LinearConstraint(root.width = a * top.width + 0)",
        "LinearConstraint(bottom.height = b)",
        "LinearConstraint(bottom.width = b)",
        "LinearConstraint(root.height = b)",
        "LinearConstraint(root.width = b)",
        "LinearConstraint(top.height = b)",
        "LinearConstraint(top.width = b)",
        "LinearConstraint(bottom.center_x = 1 * top.center_x + b)",
        "LinearConstraint(bottom.left = 1 * top.left + b)",
        "LinearConstraint(bottom.right = 1 * top.right + b)",
        "LinearConstraint(root.bottom = 1 * bottom.bottom + b)",
        "LinearConstraint(root.center_x = 1 * bottom.center_x + b)",
        "LinearConstraint(root.center_x = 1 * top.center_x + b)",
        "LinearConstraint(root.center_y = 1 * bottom.center_y + b)",
        "LinearConstraint(root.center_y = 1 * top.center_y + b)",
        "LinearConstraint(root.left = 1 * bottom.left + b)",
        "LinearConstraint(root.left = 1 * top.left + b)",
        "LinearConstraint(root.right = 1 * bottom.right + b)",
        "LinearConstraint(root.right = 1 * top.right + b)",
        "LinearConstraint(root.top = 1 * top.top + b)",
        "LinearConstraint(top.bottom = 1 * bottom.top + b)",
        "LinearConstraint(top.center_x = 1 * bottom.center_x + b)",
        "LinearConstraint(top.left = 1 * bottom.left + b)",
        "LinearConstraint(top.right = 1 * bottom.right + b)",
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
    sketches = template_instantiation([View(**example) for example in examples])
    actual_constraints = {repr(s) for s in sketches}
    expected_constraints = {
        "LinearConstraint(left.width = a * left.height + 0)",
        "LinearConstraint(right.width = a * right.height + 0)",
        "LinearConstraint(root.width = a * root.height + 0)",
        "LinearConstraint(root.height = a * left.height + 0)",
        "LinearConstraint(root.height = a * right.height + 0)",
        "LinearConstraint(root.width = a * left.width + 0)",
        "LinearConstraint(root.width = a * right.width + 0)",
        "LinearConstraint(left.height = b)",
        "LinearConstraint(left.width = b)",
        "LinearConstraint(right.height = b)",
        "LinearConstraint(right.width = b)",
        "LinearConstraint(root.height = b)",
        "LinearConstraint(root.width = b)",
        "LinearConstraint(left.bottom = 1 * right.bottom + b)",
        "LinearConstraint(left.center_y = 1 * right.center_y + b)",
        "LinearConstraint(left.right = 1 * right.left + b)",
        "LinearConstraint(left.top = 1 * right.top + b)",
        "LinearConstraint(right.bottom = 1 * left.bottom + b)",
        "LinearConstraint(right.center_y = 1 * left.center_y + b)",
        "LinearConstraint(right.top = 1 * left.top + b)",
        "LinearConstraint(root.bottom = 1 * left.bottom + b)",
        "LinearConstraint(root.bottom = 1 * right.bottom + b)",
        "LinearConstraint(root.center_x = 1 * left.center_x + b)",
        "LinearConstraint(root.center_x = 1 * right.center_x + b)",
        "LinearConstraint(root.center_y = 1 * left.center_y + b)",
        "LinearConstraint(root.center_y = 1 * right.center_y + b)",
        "LinearConstraint(root.left = 1 * left.left + b)",
        "LinearConstraint(root.right = 1 * right.right + b)",
        "LinearConstraint(root.top = 1 * left.top + b)",
        "LinearConstraint(root.top = 1 * right.top + b)",
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
    sketches = template_instantiation([View(**example) for example in examples])
    actual_constraints = {repr(s) for s in sketches}
    expected_constraints = {
        "LinearConstraint(left.width = a * left.height + 0)",
        "LinearConstraint(right.width = a * right.height + 0)",
        "LinearConstraint(root.width = a * root.height + 0)",
        "LinearConstraint(root.height = a * left.height + 0)",
        "LinearConstraint(root.height = a * right.height + 0)",
        "LinearConstraint(root.width = a * left.width + 0)",
        "LinearConstraint(root.width = a * right.width + 0)",
        "LinearConstraint(left.height = b)",
        "LinearConstraint(left.width = b)",
        "LinearConstraint(right.height = b)",
        "LinearConstraint(right.width = b)",
        "LinearConstraint(root.height = b)",
        "LinearConstraint(root.width = b)",
        "LinearConstraint(left.bottom = 1 * right.bottom + b)",
        "LinearConstraint(left.center_y = 1 * right.center_y + b)",
        "LinearConstraint(left.right = 1 * right.left + b)",
        "LinearConstraint(left.top = 1 * right.top + b)",
        "LinearConstraint(right.bottom = 1 * left.bottom + b)",
        "LinearConstraint(right.center_y = 1 * left.center_y + b)",
        "LinearConstraint(right.top = 1 * left.top + b)",
        "LinearConstraint(root.bottom = 1 * left.bottom + b)",
        "LinearConstraint(root.bottom = 1 * right.bottom + b)",
        "LinearConstraint(root.center_x = 1 * left.center_x + b)",
        "LinearConstraint(root.center_x = 1 * right.center_x + b)",
        "LinearConstraint(root.center_y = 1 * left.center_y + b)",
        "LinearConstraint(root.center_y = 1 * right.center_y + b)",
        "LinearConstraint(root.left = 1 * left.left + b)",
        "LinearConstraint(root.right = 1 * right.right + b)",
        "LinearConstraint(root.top = 1 * left.top + b)",
        "LinearConstraint(root.top = 1 * right.top + b)",
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
    actual_constraints = {repr(s) for s in sketches}
    expected_constraints = {
        "LinearConstraint(author1.width = a * author1.height + 0)",
        "LinearConstraint(author2.width = a * author2.height + 0)",
        "LinearConstraint(author3.width = a * author3.height + 0)",
        "LinearConstraint(authors.width = a * authors.height + 0)",
        "LinearConstraint(root.width = a * root.height + 0)",
        "LinearConstraint(search.width = a * search.height + 0)",
        "LinearConstraint(topbar.width = a * topbar.height + 0)",
        "LinearConstraint(authors.height = a * author1.height + 0)",
        "LinearConstraint(authors.height = a * author2.height + 0)",
        "LinearConstraint(authors.height = a * author3.height + 0)",
        "LinearConstraint(authors.width = a * author1.width + 0)",
        "LinearConstraint(authors.width = a * author2.width + 0)",
        "LinearConstraint(authors.width = a * author3.width + 0)",
        "LinearConstraint(root.height = a * authors.height + 0)",
        "LinearConstraint(root.height = a * search.height + 0)",
        "LinearConstraint(root.height = a * topbar.height + 0)",
        "LinearConstraint(root.width = a * authors.width + 0)",
        "LinearConstraint(root.width = a * search.width + 0)",
        "LinearConstraint(root.width = a * topbar.width + 0)",
        "LinearConstraint(author1.height = b)",
        "LinearConstraint(author1.width = b)",
        "LinearConstraint(author2.height = b)",
        "LinearConstraint(author2.width = b)",
        "LinearConstraint(author3.height = b)",
        "LinearConstraint(author3.width = b)",
        "LinearConstraint(authors.height = b)",
        "LinearConstraint(authors.width = b)",
        "LinearConstraint(root.height = b)",
        "LinearConstraint(root.width = b)",
        "LinearConstraint(search.height = b)",
        "LinearConstraint(search.width = b)",
        "LinearConstraint(topbar.height = b)",
        "LinearConstraint(topbar.width = b)",
        "LinearConstraint(author1.bottom = 1 * author2.bottom + b)",
        "LinearConstraint(author1.center_y = 1 * author2.center_y + b)",
        "LinearConstraint(author1.right = 1 * author2.left + b)",
        "LinearConstraint(author1.top = 1 * author2.top + b)",
        "LinearConstraint(author2.bottom = 1 * author1.bottom + b)",
        "LinearConstraint(author2.bottom = 1 * author3.bottom + b)",
        "LinearConstraint(author2.center_y = 1 * author1.center_y + b)",
        "LinearConstraint(author2.center_y = 1 * author3.center_y + b)",
        "LinearConstraint(author2.right = 1 * author3.left + b)",
        "LinearConstraint(author2.top = 1 * author1.top + b)",
        "LinearConstraint(author2.top = 1 * author3.top + b)",
        "LinearConstraint(author3.bottom = 1 * author2.bottom + b)",
        "LinearConstraint(author3.center_y = 1 * author2.center_y + b)",
        "LinearConstraint(author3.top = 1 * author2.top + b)",
        "LinearConstraint(authors.bottom = 1 * author1.bottom + b)",
        "LinearConstraint(authors.bottom = 1 * author2.bottom + b)",
        "LinearConstraint(authors.bottom = 1 * author3.bottom + b)",
        "LinearConstraint(authors.center_x = 1 * author1.center_x + b)",
        "LinearConstraint(authors.center_x = 1 * author3.center_x + b)",
        "LinearConstraint(authors.center_x = 1 * search.center_x + b)",
        "LinearConstraint(authors.center_y = 1 * author1.center_y + b)",
        "LinearConstraint(authors.center_y = 1 * author2.center_y + b)",
        "LinearConstraint(authors.center_y = 1 * author3.center_y + b)",
        "LinearConstraint(authors.left = 1 * author1.left + b)",
        "LinearConstraint(authors.left = 1 * search.left + b)",
        "LinearConstraint(authors.right = 1 * author3.right + b)",
        "LinearConstraint(authors.right = 1 * search.right + b)",
        "LinearConstraint(authors.top = 1 * author1.top + b)",
        "LinearConstraint(authors.top = 1 * author2.top + b)",
        "LinearConstraint(authors.top = 1 * author3.top + b)",
        "LinearConstraint(root.bottom = 1 * authors.bottom + b)",
        "LinearConstraint(root.center_x = 1 * authors.center_x + b)",
        "LinearConstraint(root.center_x = 1 * search.center_x + b)",
        "LinearConstraint(root.center_x = 1 * topbar.center_x + b)",
        "LinearConstraint(root.center_y = 1 * authors.center_y + b)",
        "LinearConstraint(root.center_y = 1 * topbar.center_y + b)",
        "LinearConstraint(root.left = 1 * authors.left + b)",
        "LinearConstraint(root.left = 1 * search.left + b)",
        "LinearConstraint(root.left = 1 * topbar.left + b)",
        "LinearConstraint(root.right = 1 * authors.right + b)",
        "LinearConstraint(root.right = 1 * search.right + b)",
        "LinearConstraint(root.right = 1 * topbar.right + b)",
        "LinearConstraint(root.top = 1 * topbar.top + b)",
        "LinearConstraint(search.bottom = 1 * authors.top + b)",
        "LinearConstraint(search.center_x = 1 * authors.center_x + b)",
        "LinearConstraint(search.center_x = 1 * topbar.center_x + b)",
        "LinearConstraint(search.left = 1 * authors.left + b)",
        "LinearConstraint(search.left = 1 * topbar.left + b)",
        "LinearConstraint(search.right = 1 * authors.right + b)",
        "LinearConstraint(search.right = 1 * topbar.right + b)",
        "LinearConstraint(topbar.bottom = 1 * search.top + b)",
        "LinearConstraint(topbar.center_x = 1 * search.center_x + b)",
        "LinearConstraint(topbar.left = 1 * search.left + b)",
        "LinearConstraint(topbar.right = 1 * search.right + b)",
    }
    assert actual_constraints == expected_constraints
