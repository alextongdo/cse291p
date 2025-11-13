"""Tests for evaluation metrics."""

import pytest
import sympy as sym

from cse291p.pipeline.view import View
from cse291p.pipeline.view.builder import ViewBuilder
from cse291p.pipeline.view.primitives import Attribute
from cse291p.evaluation import (
    get_view_ltwh,
    get_view_corners,
    calculate_rmsd,
    calculate_accuracy,
    evaluate_single_example,
    group_by_isomorphic_structure,
    evaluate_layouts,
)


def test_get_view_corners():
    """Test LTWH extraction from view hierarchy (backward compatibility alias)."""
    # Create a simple view hierarchy
    root = ViewBuilder(
        name="root",
        rect=(0, 0, 100, 100),
        children=[
            ViewBuilder(name="child1", rect=(10, 10, 50, 50), children=[]),
            ViewBuilder(name="child2", rect=(60, 10, 90, 50), children=[]),
        ]
    ).build(number_type=sym.Rational)
    
    corners = get_view_corners(root)
    
    assert "root" in corners
    assert "child1" in corners
    assert "child2" in corners
    
    # get_view_corners now returns LTWH format: (left, top, width, height)
    assert corners["root"] == (0.0, 0.0, 100.0, 100.0)
    assert corners["child1"] == (10.0, 10.0, 40.0, 40.0)  # width=50-10, height=50-10
    assert corners["child2"] == (60.0, 10.0, 30.0, 40.0)  # width=90-60, height=50-10


def test_calculate_rmsd():
    """Test RMSD calculation using LTWH format (matches auto-mock)."""
    # LTWH format: (left, top, width, height)
    original = {
        "view1": (10.0, 20.0, 40.0, 40.0),  # left, top, width, height
        "view2": (0.0, 0.0, 100.0, 100.0),
    }
    
    # Perfect match
    synthesized = {
        "view1": (10.0, 20.0, 40.0, 40.0),
        "view2": (0.0, 0.0, 100.0, 100.0),
    }
    
    rmsd = calculate_rmsd(original, synthesized)
    assert rmsd == 0.0
    
    # 1 pixel difference in left coordinate only
    synthesized = {
        "view1": (11.0, 20.0, 40.0, 40.0),  # left differs by 1
        "view2": (0.0, 0.0, 100.0, 100.0),
    }
    
    rmsd = calculate_rmsd(original, synthesized)
    # 1 difference squared = 1, count = 8 (2 views * 4 dimensions), sqrt(1/8)
    assert abs(rmsd - (1.0 / (8 ** 0.5))) < 0.001


def test_calculate_accuracy():
    """Test accuracy calculation."""
    original = {
        "view1": (10.0, 20.0, 50.0, 60.0),
        "view2": (0.0, 0.0, 100.0, 100.0),
    }
    
    # Perfect match
    synthesized = {
        "view1": (10.0, 20.0, 50.0, 60.0),
        "view2": (0.0, 0.0, 100.0, 100.0),
    }
    
    accuracy = calculate_accuracy(original, synthesized)
    assert accuracy == 100.0
    
    # One view within threshold, one not
    synthesized = {
        "view1": (10.5, 20.0, 50.0, 60.0),  # within 1 pixel
        "view2": (0.0, 0.0, 100.0, 101.5),  # bottom differs by 1.5 pixels
    }
    
    accuracy = calculate_accuracy(original, synthesized, threshold=1.0)
    assert accuracy == 50.0  # Only view1 is accurate


def test_group_by_isomorphic_structure():
    """Test grouping by isomorphic structure."""
    # Create two groups: 2-column and 1-column layouts
    two_col_1 = ViewBuilder(
        name="root",
        rect=(0, 0, 100, 100),
        children=[
            ViewBuilder(name="col1", rect=(0, 0, 50, 100), children=[]),
            ViewBuilder(name="col2", rect=(50, 0, 100, 100), children=[]),
        ]
    ).build(number_type=sym.Rational)
    
    two_col_2 = ViewBuilder(
        name="root",
        rect=(0, 0, 200, 100),
        children=[
            ViewBuilder(name="col1", rect=(0, 0, 100, 100), children=[]),
            ViewBuilder(name="col2", rect=(100, 0, 200, 100), children=[]),
        ]
    ).build(number_type=sym.Rational)
    
    one_col_1 = ViewBuilder(
        name="root",
        rect=(0, 0, 100, 200),
        children=[
            ViewBuilder(name="col1", rect=(0, 0, 100, 200), children=[]),
        ]
    ).build(number_type=sym.Rational)
    
    examples = [two_col_1, two_col_2, one_col_1]
    groups = group_by_isomorphic_structure(examples)
    
    assert len(groups) == 2
    assert len(groups[0]) == 2  # Two 2-column examples
    assert len(groups[1]) == 1  # One 1-column example


def test_evaluate_single_example():
    """Test single example evaluation."""
    # Create a simple view
    root = ViewBuilder(
        name="root",
        rect=(0, 0, 100, 100),
        children=[
            ViewBuilder(name="child", rect=(10, 10, 50, 50), children=[]),
        ]
    ).build(number_type=sym.Rational)
    
    # Create a constraint: child.left = root.left + 10
    from cse291p.pipeline.view.primitives import AnchorID
    from cse291p.pipeline.constraint.constraint import LinearConstraint
    from cse291p.pipeline.constraint.types import ConstraintKind
    import operator
    
    child_left = AnchorID(view_name="child", attribute=Attribute.LEFT)
    root_left = AnchorID(view_name="root", attribute=Attribute.LEFT)
    
    # child.left = root.left + 10
    constraint = LinearConstraint(
        kind=ConstraintKind.POS_LTRB_OFFSET,
        y_id=child_left,
        x_id=root_left,
        a=sym.Rational(1),
        b=sym.Rational(10),
        op=operator.eq
    )
    
    synthesized = evaluate_single_example(root, [constraint])
    
    # Check that child.left is approximately 10
    assert abs(float(synthesized.find_view("child").left) - 10.0) < 0.1


def test_evaluate_layouts_single_structure():
    """Test evaluation for single-structure layouts."""
    # Create two isomorphic examples
    ex1 = ViewBuilder(
        name="root",
        rect=(0, 0, 100, 100),
        children=[
            ViewBuilder(name="child", rect=(10, 10, 50, 50), children=[]),
        ]
    ).build(number_type=sym.Rational)
    
    ex2 = ViewBuilder(
        name="root",
        rect=(0, 0, 200, 200),
        children=[
            ViewBuilder(name="child", rect=(10, 10, 50, 50), children=[]),
        ]
    ).build(number_type=sym.Rational)
    
    # Empty constraints (should produce some error, but shouldn't crash)
    result = evaluate_layouts([ex1, ex2], [], conditional=False)
    
    assert 'rmsd' in result
    assert 'accuracy' in result
    assert result['num_examples'] == 2
    assert result['num_groups'] == 1

