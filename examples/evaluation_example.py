"""Example script demonstrating how to use the evaluation metrics.

This script shows how to:
1. Evaluate synthesized constraints against original examples
2. Calculate RMSD and accuracy metrics
3. Handle both single-structure and conditional layouts
"""

import json
from pathlib import Path

from cse291p.pipeline.input import load_from_file
from cse291p.pipeline.run import synthesize
from cse291p.pipeline.view.loader import ViewLoader
from cse291p.pipeline.constraint import IConstraint
from cse291p.evaluation import evaluate_layouts
import sympy as sym


def example_single_structure_evaluation():
    """Example: Evaluate single-structure layout synthesis."""
    print("Example 1: Single-Structure Evaluation")
    print("-" * 50)
    
    # Load test input
    input_file = Path("tests/inputs/1x1_fixed-ltwh.json")
    if not input_file.exists():
        print(f"Test file not found: {input_file}")
        return
    
    # Load examples
    loader = ViewLoader(number_type=sym.Rational, input_format='default')
    with input_file.open('r') as f:
        input_data = json.load(f)
    
    examples = [loader.load_dict(ex) for ex in input_data['examples']]
    print(f"Loaded {len(examples)} examples")
    
    # Synthesize constraints
    options = {
        'input_format': 'default',
        'numeric_type': 'N',
        'instantiation_method': 'numpy',
        'learning_method': 'noisetolerant',
        'pruning_method': 'baseline',
        'unambig': False,
    }
    
    result = synthesize(input_data, options)
    constraints = result['constraints']
    print(f"Synthesized {len(constraints)} constraints")
    
    # Convert constraints back to IConstraint objects for evaluation
    # Note: In practice, you'd want to keep the constraint objects from synthesis
    # For this example, we'll just show the structure
    print("\nNote: Full evaluation requires IConstraint objects.")
    print("In practice, modify synthesize() to return constraint objects, not just dicts.")


def example_conditional_evaluation():
    """Example: Evaluate conditional layout synthesis."""
    print("\nExample 2: Conditional Layout Evaluation")
    print("-" * 50)
    
    print("For conditional layouts with structural variations:")
    print("1. Group examples by isomorphic structure")
    print("2. Evaluate each group separately")
    print("3. Average metrics across groups")
    print("\nExample usage:")
    print("""
    from cse291p.evaluation import evaluate_layouts
    
    # Assuming you have examples and constraints
    result = evaluate_layouts(
        examples=examples,
        constraints=constraints,
        conditional=True  # Enable conditional evaluation
    )
    
    print(f"RMSD: {result['rmsd']:.2f} pixels")
    print(f"Accuracy: {result['accuracy']:.1f}%")
    print(f"Number of structural groups: {result['num_groups']}")
    
    # View per-group results
    for i, group_result in enumerate(result['group_results']):
        print(f"Group {i+1}: RMSD={group_result['rmsd']:.2f}, "
              f"Accuracy={group_result['accuracy']:.1f}%")
    """)


def example_manual_evaluation():
    """Example: Manual evaluation step-by-step."""
    print("\nExample 3: Manual Evaluation Steps")
    print("-" * 50)
    
    print("""
    # Step 1: Get corners from original and synthesized views
    from cse291p.evaluation import get_view_corners, calculate_rmsd, calculate_accuracy
    
    original_corners = get_view_corners(original_view)
    synthesized_corners = get_view_corners(synthesized_view)
    
    # Step 2: Calculate metrics
    rmsd = calculate_rmsd(original_corners, synthesized_corners)
    accuracy = calculate_accuracy(original_corners, synthesized_corners)
    
    print(f"RMSD: {rmsd:.2f} pixels")
    print(f"Accuracy: {accuracy:.1f}%")
    
    # Step 3: Interpret results
    # - RMSD < 1.0: Excellent (sub-pixel accuracy)
    # - RMSD < 5.0: Good (within a few pixels)
    # - RMSD > 10.0: Poor (significant errors)
    #
    # - Accuracy > 90%: Excellent
    # - Accuracy > 70%: Good
    # - Accuracy < 50%: Poor
    """)


if __name__ == "__main__":
    print("Evaluation Metrics Examples")
    print("=" * 50)
    print("\nThis module implements evaluation metrics from the Mockdown paper:")
    print("- RMSD: Root Mean Square Deviation of view corners")
    print("- Accuracy: Percentage of views within 1 pixel of original")
    print()
    
    example_single_structure_evaluation()
    example_conditional_evaluation()
    example_manual_evaluation()
    
    print("\n" + "=" * 50)
    print("For more details, see:")
    print("- src/cse291p/evaluation/metrics.py")
    print("- tests/test_evaluation_metrics.py")

