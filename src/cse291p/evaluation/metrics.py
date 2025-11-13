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


def get_view_ltwh(view: IView[NT]) -> Dict[str, Tuple[float, float, float, float]]:
    """Extract (left, top, width, height) for all views in hierarchy.
    
    Matches auto-mock's Tree.ts implementation which uses left, top, width, height.
    
    Returns a dictionary mapping view names to their LTWH coordinates.
    Each tuple is (left, top, width, height) in pixels.
    
    Args:
        view: Root view of the hierarchy
    
    Returns:
        Dictionary mapping view names to (left, top, width, height) tuples
    """
    ltwh = {}
    for v in traverse(view, include_self=True, deep=True):
        # Convert to float for comparison
        left = float(v.left)
        top = float(v.top)
        width = float(v.width)
        height = float(v.height)
        ltwh[v.name] = (left, top, width, height)
    return ltwh


# Backward compatibility alias
def get_view_corners(view: IView[NT]) -> Dict[str, Tuple[float, float, float, float]]:
    """Deprecated: Use get_view_ltwh instead.
    
    For backward compatibility, this returns (left, top, width, height).
    """
    return get_view_ltwh(view)


def calculate_rmsd(
    original_ltwh: Dict[str, Tuple[float, float, float, float]],
    synthesized_ltwh: Dict[str, Tuple[float, float, float, float]]
) -> float:
    """Calculate Root Mean Square Deviation between original and synthesized views.
    
    Matches auto-mock's Tree.ts implementation:
    - totalSquareDiff: (left - left')^2 + (top - top')^2 + (width - width')^2 + (height - height')^2
    - squaredErr: sum of totalSquareDiff across all views in hierarchy
    - rms: sqrt(squaredErr / count)
    
    RMSD = sqrt(sum((original - synthesized)^2) / count)
    where we compute squared difference for left, top, width, height for each view.
    
    Args:
        original_ltwh: Dict mapping view names to (left, top, width, height) tuples
        synthesized_ltwh: Dict mapping view names to (left, top, width, height) tuples
    
    Returns:
        RMSD value in pixels. Returns float('inf') if no common views exist.
    """
    squared_err = 0.0
    count = 0
    
    # Only compare views that exist in both
    common_views = set(original_ltwh.keys()) & set(synthesized_ltwh.keys())
    
    if not common_views:
        return float('inf')  # No common views to compare
    
    for view_name in common_views:
        orig = original_ltwh[view_name]
        synth = synthesized_ltwh[view_name]
        
        # Calculate squared difference for each dimension (left, top, width, height)
        # This matches auto-mock's totalSquareDiff
        for i in range(4):
            diff = orig[i] - synth[i]
            squared_err += diff * diff
            count += 1
    
    if count == 0:
        return 0.0
    
    # This matches auto-mock's: Math.sqrt(err/this.count())
    return math.sqrt(squared_err / count)


def calculate_accuracy(
    original_ltwh: Dict[str, Tuple[float, float, float, float]],
    synthesized_ltwh: Dict[str, Tuple[float, float, float, float]],
    threshold: float = 1.0
) -> float:
    """Calculate accuracy: percentage of views within threshold pixels of original.
    
    A view is considered "accurate" if all four values (left, top, width, height)
    are within threshold pixels of the original.
    
    Args:
        original_ltwh: Dict mapping view names to (left, top, width, height) tuples
        synthesized_ltwh: Dict mapping view names to (left, top, width, height) tuples
        threshold: Pixel threshold (default: 1.0 pixel)
    
    Returns:
        Accuracy as a percentage (0.0 to 100.0). Returns 0.0 if no common views exist.
    """
    common_views = set(original_ltwh.keys()) & set(synthesized_ltwh.keys())
    
    if not common_views:
        return 0.0
    
    accurate_views = 0
    
    for view_name in common_views:
        orig = original_ltwh[view_name]
        synth = synthesized_ltwh[view_name]
        
        # Check if all four dimensions are within threshold
        all_within_threshold = all(
            abs(orig[i] - synth[i]) <= threshold
            for i in range(4)  # left, top, width, height
        )
        
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
        
        # Get LTWH for comparison (matches auto-mock)
        original_ltwh = get_view_ltwh(original_view)
        synthesized_ltwh = get_view_ltwh(synthesized_view)
        
        # Calculate metrics
        rmsd = calculate_rmsd(original_ltwh, synthesized_ltwh)
        accuracy = calculate_accuracy(original_ltwh, synthesized_ltwh)
        
        rmsds.append(rmsd)
        accuracies.append(accuracy)
    
    # Average across all examples
    avg_rmsd = sum(rmsds) / len(rmsds) if rmsds else float('inf')
    avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0.0
    
    return {
        'rmsd': avg_rmsd,
        'accuracy': avg_accuracy,
        'num_examples': len(examples),
        'per_example_rmsd': rmsds,  # Keep individual scores for conditional implementation
        'per_example_accuracy': accuracies
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
    if not examples:
        return {
            'rmsd': float('inf'),
            'accuracy': 0.0,
            'num_examples': 0,
            'per_example_rmsd': [],
            'per_example_accuracy': []
        }
    
    if not conditional:
        # Single structure: evaluate all examples together
        return evaluate_single_structure(examples, constraints)
    
    # Conditional layout: group by isomorphic structure
    groups = group_by_isomorphic_structure(examples)
    
    if not groups:
        return {
            'rmsd': float('inf'),
            'accuracy': 0.0,
            'num_examples': 0,
            'num_groups': 0,
            'groups': [],
            'per_example_rmsd': [],
            'per_example_accuracy': []
        }
    
    # Evaluate each group
    group_results = []
    for i, group in enumerate(groups):
        group_result = evaluate_single_structure(group, constraints)
        group_result['group_id'] = i
        group_result['group_size'] = len(group)
        group_results.append(group_result)
    
    # Aggregate across all groups
    all_rmsds = []
    all_accuracies = []
    for result in group_results:
        all_rmsds.extend(result['per_example_rmsd'])
        all_accuracies.extend(result['per_example_accuracy'])
    
    avg_rmsd = sum(all_rmsds) / len(all_rmsds) if all_rmsds else float('inf')
    avg_accuracy = sum(all_accuracies) / len(all_accuracies) if all_accuracies else 0.0
    
    return {
        'rmsd': avg_rmsd,
        'accuracy': avg_accuracy,
        'num_examples': len(examples),
        'num_groups': len(groups),
        'groups': group_results,
        'per_example_rmsd': all_rmsds,
        'per_example_accuracy': all_accuracies
    }

