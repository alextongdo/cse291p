"""Evaluation metrics for layout synthesis.

Implements RMSD and accuracy metrics from the Mockdown paper.
"""

import math
from typing import List, Dict, Tuple, Optional, Any

import sympy as sym

from cse291p.pipeline.view import IView
from cse291p.pipeline.view.primitives import Rect
from cse291p.pipeline.constraint import IConstraint
from cse291p.pipeline.integration.kiwi import evaluate_constraints
from cse291p.pipeline.view.ops import is_isomorphic, traverse
from cse291p.types import NT


def get_view_corners(view: IView[NT]) -> Dict[str, Tuple[float, float, float, float]]:
    """Extract corners (left, top, right, bottom) for all views in hierarchy.
    
    Returns a dictionary mapping view names to their corner coordinates.
    Each corner tuple is (left, top, right, bottom) in pixels.
    
    Args:
        view: Root view of the hierarchy
    
    Returns:
        Dictionary mapping view names to (left, top, right, bottom) tuples
    """
    corners = {}
    for v in traverse(view, include_self=True, deep=True):
        # Convert to float for comparison
        left = float(v.left)
        top = float(v.top)
        right = float(v.right)
        bottom = float(v.bottom)
        corners[v.name] = (left, top, right, bottom)
    return corners


def calculate_rmsd(
    original_corners: Dict[str, Tuple[float, float, float, float]],
    synthesized_corners: Dict[str, Tuple[float, float, float, float]]
) -> float:
    """Calculate Root Mean Square Deviation between original and synthesized view corners.
    
    RMSD = sqrt(mean((original_corner - synthesized_corner)^2))
    where we compute the squared difference for each of the 4 corners (left, top, right, bottom)
    for each view, then take the mean and square root.
    
    Args:
        original_corners: Dict mapping view names to (left, top, right, bottom) tuples
        synthesized_corners: Dict mapping view names to (left, top, right, bottom) tuples
    
    Returns:
        RMSD value in pixels. Returns float('inf') if no common views exist.
    """
    squared_diffs = []
    
    # Only compare views that exist in both
    common_views = set(original_corners.keys()) & set(synthesized_corners.keys())
    
    if not common_views:
        return float('inf')  # No common views to compare
    
    for view_name in common_views:
        orig = original_corners[view_name]
        synth = synthesized_corners[view_name]
        
        # Calculate squared difference for each corner coordinate
        for i in range(4):  # left, top, right, bottom
            diff = orig[i] - synth[i]
            squared_diffs.append(diff * diff)
    
    if not squared_diffs:
        return 0.0
    
    mean_squared_diff = sum(squared_diffs) / len(squared_diffs)
    return math.sqrt(mean_squared_diff)


def calculate_accuracy(
    original_corners: Dict[str, Tuple[float, float, float, float]],
    synthesized_corners: Dict[str, Tuple[float, float, float, float]],
    threshold: float = 1.0
) -> float:
    """Calculate accuracy: percentage of views within threshold pixels of original.
    
    A view is considered "accurate" if all four corners (left, top, right, bottom)
    are within threshold pixels of the original.
    
    Args:
        original_corners: Dict mapping view names to (left, top, right, bottom) tuples
        synthesized_corners: Dict mapping view names to (left, top, right, bottom) tuples
        threshold: Pixel threshold (default: 1.0 pixel)
    
    Returns:
        Accuracy as a percentage (0.0 to 100.0). Returns 0.0 if no common views exist.
    """
    common_views = set(original_corners.keys()) & set(synthesized_corners.keys())
    
    if not common_views:
        return 0.0
    
    accurate_views = 0
    
    for view_name in common_views:
        orig = original_corners[view_name]
        synth = synthesized_corners[view_name]
        
        # Check if all corners are within threshold
        all_within_threshold = True
        for i in range(4):  # left, top, right, bottom
            diff = abs(orig[i] - synth[i])
            if diff > threshold:
                all_within_threshold = False
                break
        
        if all_within_threshold:
            accurate_views += 1
    
    return (accurate_views / len(common_views)) * 100.0


def evaluate_single_example(
    original_view: IView[NT],
    constraints: List[IConstraint],
    root_rect: Optional[Rect[sym.Rational]] = None
) -> IView[sym.Float]:
    """Evaluate constraints on a single example view.
    
    Solves the constraints using the Kiwi solver and returns a synthesized view
    hierarchy with solved coordinates.
    
    Args:
        original_view: The original view hierarchy (used as skeleton structure)
        constraints: List of synthesized constraints to evaluate
        root_rect: Root rectangle bounds (if None, uses original_view's rect)
    
    Returns:
        Synthesized view hierarchy with solved coordinates (Float type)
    """
    if root_rect is None:
        # Use original view's rect as bounds
        root_rect = Rect(
            left=sym.Rational(original_view.left),
            top=sym.Rational(original_view.top),
            right=sym.Rational(original_view.right),
            bottom=sym.Rational(original_view.bottom)
        )
    
    # Evaluate constraints using Kiwi solver
    synthesized_view = evaluate_constraints(
        view=original_view,
        top_rect=root_rect,
        constraints=constraints,
        strength='strong'
    )
    
    return synthesized_view


def evaluate_single_structure(
    examples: List[IView[NT]],
    constraints: List[IConstraint]
) -> Dict[str, Any]:
    """Evaluate constraints on a set of examples with the same structure.
    
    Evaluates each example independently and averages the metrics across all examples.
    Used for single-structure layouts (original Mockdown behavior).
    
    Args:
        examples: List of example views (all should be isomorphic)
        constraints: List of synthesized constraints
    
    Returns:
        Dictionary with 'rmsd', 'accuracy', and 'num_examples' keys
    """
    rmsds = []
    accuracies = []
    
    for original_view in examples:
        # Evaluate constraints for this example
        synthesized_view = evaluate_single_example(original_view, constraints)
        
        # Get corners for comparison
        original_corners = get_view_corners(original_view)
        synthesized_corners = get_view_corners(synthesized_view)
        
        # Calculate metrics
        rmsd = calculate_rmsd(original_corners, synthesized_corners)
        accuracy = calculate_accuracy(original_corners, synthesized_corners)
        
        rmsds.append(rmsd)
        accuracies.append(accuracy)
    
    # Average across all examples
    avg_rmsd = sum(rmsds) / len(rmsds) if rmsds else float('inf')
    avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0.0
    
    return {
        'rmsd': avg_rmsd,
        'accuracy': avg_accuracy,
        'num_examples': len(examples)
    }


def group_by_isomorphic_structure(
    examples: List[IView[NT]]
) -> List[List[IView[NT]]]:
    """Group examples by isomorphic structure.
    
    Examples with the same structure (same number of children at each level,
    same view names) are grouped together. This is used for conditional layouts
    where different screen sizes may have different structures.
    
    Args:
        examples: List of example views
    
    Returns:
        List of groups, where each group contains isomorphic examples
    """
    groups: List[List[IView[NT]]] = []
    assigned = [False] * len(examples)
    
    for i, example in enumerate(examples):
        if assigned[i]:
            continue
        
        # Start a new group with this example
        group = [example]
        assigned[i] = True
        
        # Find all other examples isomorphic to this one
        for j, other in enumerate(examples[i+1:], start=i+1):
            if assigned[j]:
                continue
            
            if is_isomorphic(example, other, include_names=True):
                group.append(other)
                assigned[j] = True
        
        groups.append(group)
    
    return groups


def evaluate_layouts(
    examples: List[IView[NT]],
    constraints: List[IConstraint],
    conditional: bool = False
) -> Dict[str, Any]:
    """Evaluate synthesized constraints against original examples.
    
    For single-structure layouts: evaluates all examples together.
    For conditional layouts: groups by isomorphic structure, evaluates each group,
    and averages the results.
    
    Args:
        examples: List of original example views
        constraints: List of synthesized constraints
        conditional: If True, treat as conditional layout (group by structure)
    
    Returns:
        Dictionary with evaluation metrics:
        - 'rmsd': Root Mean Square Deviation (pixels)
        - 'accuracy': Percentage of views within 1 pixel (0-100)
        - 'num_examples': Number of examples evaluated
        - 'num_groups': Number of structural groups (for conditional layouts)
        - 'group_results': Per-group results (for conditional layouts)
    """
    if not conditional:
        # Single structure: evaluate all examples together
        result = evaluate_single_structure(examples, constraints)
        result['num_groups'] = 1
        result['group_results'] = [result]
        return result
    
    # Conditional layout: group by isomorphic structure
    groups = group_by_isomorphic_structure(examples)
    
    if not groups:
        return {
            'rmsd': float('inf'),
            'accuracy': 0.0,
            'num_examples': 0,
            'num_groups': 0,
            'group_results': []
        }
    
    # Evaluate each group
    group_results = []
    for group in groups:
        group_result = evaluate_single_structure(group, constraints)
        group_results.append(group_result)
    
    # Average metrics across all groups
    avg_rmsd = sum(r['rmsd'] for r in group_results) / len(group_results)
    avg_accuracy = sum(r['accuracy'] for r in group_results) / len(group_results)
    
    return {
        'rmsd': avg_rmsd,
        'accuracy': avg_accuracy,
        'num_examples': len(examples),
        'num_groups': len(groups),
        'group_results': group_results
    }

