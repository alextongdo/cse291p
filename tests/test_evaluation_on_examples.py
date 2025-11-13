"""Test evaluation metrics on existing test inputs and outputs.

This test runs the full pipeline and evaluates the synthesized constraints
against the original examples using RMSD and accuracy metrics.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

import sympy as sym
import operator

from cse291p.pipeline.input import load_from_file
from cse291p.pipeline.view.loader import ViewLoader
from cse291p.pipeline.view import IView
from cse291p.pipeline.constraint import IConstraint, LinearConstraint, ConstantConstraint
from cse291p.pipeline.constraint.types import ConstraintKind
from cse291p.pipeline.view.types import AnchorID
from cse291p.pipeline.view.primitives import Attribute
from cse291p.evaluation import evaluate_layouts

# Import pipeline components directly to get constraint objects
from cse291p.pipeline.sketch_generation.numpy import NumpyConstraintInstantiator
from cse291p.pipeline.bayes.noisetolerant.learning import NoiseTolerantLearning
from cse291p.pipeline.bayes.noisetolerant.types import NoiseTolerantLearningConfig
from cse291p.pipeline.hierarchical_decomp.blackbox import BlackBoxPruner


def parse_anchor_id(anchor_str: str) -> AnchorID:
    """Parse anchor ID from string like 'child.width' or 'root.left'."""
    parts = anchor_str.split('.')
    if len(parts) != 2:
        raise ValueError(f"Invalid anchor format: {anchor_str}")
    view_name, attr_name = parts
    attr = Attribute[attr_name.upper()]
    return AnchorID(view_name=view_name, attribute=attr)


def dict_to_constraint(constraint_dict: Dict[str, str]) -> IConstraint:
    """Convert constraint dictionary to IConstraint object."""
    kind_str = constraint_dict['kind']
    kind = ConstraintKind[kind_str.upper()]
    
    y_id = parse_anchor_id(constraint_dict['y'])
    x_id = None
    if 'x' in constraint_dict:
        x_id = parse_anchor_id(constraint_dict['x'])
    
    # Parse operator
    op_str = constraint_dict.get('op', '=')
    if op_str == '=':
        op = operator.eq
    elif op_str == '≤':
        op = operator.le
    elif op_str == '≥':
        op = operator.ge
    else:
        op = operator.eq
    
    # Parse a and b
    a = sym.Rational(0)
    b = sym.Rational(0)
    
    if 'a' in constraint_dict:
        a = sym.Rational(constraint_dict['a'])
    if 'b' in constraint_dict:
        b = sym.Rational(constraint_dict['b'])
    
    # Create appropriate constraint type
    if x_id is None:
        # Constant constraint: y = b
        return ConstantConstraint(
            kind=kind,
            y_id=y_id,
            b=b,
            op=op,
            sample_count=1
        )
    else:
        # Linear constraint: y = a*x + b
        return LinearConstraint(
            kind=kind,
            y_id=y_id,
            x_id=x_id,
            a=a,
            b=b,
            op=op,
            sample_count=1
        )


def evaluate_test_case(input_file: Path, output_file: Path = None) -> Dict[str, Any]:
    """Evaluate a single test case."""
    print(f"\n{'='*60}")
    print(f"Testing: {input_file.name}")
    print('='*60)
    
    # Load input
    with input_file.open('r') as f:
        input_data = json.load(f)
    
    # Load examples
    loader = ViewLoader(number_type=sym.Rational, input_format='default')
    examples = [loader.load_dict(ex) for ex in input_data['examples']]
    print(f"Loaded {len(examples)} examples")
    
    # Run synthesis pipeline manually to get constraint objects
    print("Running synthesis...")
    
    # 1. Sketch generation
    instantiator = NumpyConstraintInstantiator(examples)
    templates = instantiator.instantiate()
    print(f"  Generated {len(templates)} constraint templates")
    
    # 2. Learning
    max_offset = max((max(ex.width, ex.height) for ex in examples)) + 10
    cfg = NoiseTolerantLearningConfig(sample_count=len(examples), max_offset=max_offset)
    learner = NoiseTolerantLearning(templates=templates, samples=examples, config=cfg)
    candidate_lists = learner.learn()
    candidates = [c for lst in candidate_lists for c in lst]
    print(f"  Learned {len(candidates)} candidate constraints")
    
    # 3. Global inference (pruning)
    root = examples[0]
    min_w = min(e.width for e in examples)
    min_h = min(e.height for e in examples)
    max_w = max(e.width for e in examples)
    max_h = max(e.height for e in examples)
    bounds = {
        'min_w': sym.Rational(min_w),
        'min_h': sym.Rational(min_h),
        'max_w': sym.Rational(max_w),
        'max_h': sym.Rational(max_h),
    }
    
    pruner = BlackBoxPruner(examples, bounds, solve_unambig=False, targets=[root] + list(root.children))
    pruned_constraints, min_vals, max_vals = pruner(candidates)
    print(f"  Pruned to {len(pruned_constraints)} constraints")
    
    # Evaluate
    print("Evaluating metrics...")
    eval_result = evaluate_layouts(examples, pruned_constraints, conditional=False)
    
    # Print results
    print(f"\nResults:")
    print(f"  RMSD: {eval_result['rmsd']:.4f} pixels")
    print(f"  Accuracy: {eval_result['accuracy']:.2f}%")
    print(f"  Number of examples: {eval_result['num_examples']}")
    
    # Compare with expected output if available
    if output_file and output_file.exists():
        with output_file.open('r') as f:
            expected_output = json.load(f)
        expected_constraints = expected_output.get('constraints', [])
        print(f"\nExpected {len(expected_constraints)} constraints")
        print(f"Got {len(pruned_constraints)} constraints")
    
    return {
        'input_file': input_file.name,
        'rmsd': eval_result['rmsd'],
        'accuracy': eval_result['accuracy'],
        'num_examples': eval_result['num_examples'],
        'num_constraints': len(pruned_constraints),
    }


def main():
    """Run evaluation on all test cases."""
    test_dir = Path(__file__).parent
    inputs_dir = test_dir / 'inputs'
    outputs_dir = test_dir / 'outputs' / 'refactored'
    
    # Get all test input files
    input_files = sorted(inputs_dir.glob('*.json'))
    
    if not input_files:
        print(f"No test files found in {inputs_dir}")
        return
    
    print(f"Found {len(input_files)} test cases")
    
    results = []
    for input_file in input_files:
        output_file = outputs_dir / input_file.name
        try:
            result = evaluate_test_case(input_file, output_file)
            results.append(result)
        except Exception as e:
            print(f"\nERROR evaluating {input_file.name}: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'input_file': input_file.name,
                'error': str(e)
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    
    successful = [r for r in results if 'error' not in r]
    failed = [r for r in results if 'error' in r]
    
    if successful:
        avg_rmsd = sum(r['rmsd'] for r in successful) / len(successful)
        avg_accuracy = sum(r['accuracy'] for r in successful) / len(successful)
        
        print(f"\nSuccessful evaluations: {len(successful)}/{len(results)}")
        print(f"Average RMSD: {avg_rmsd:.4f} pixels")
        print(f"Average Accuracy: {avg_accuracy:.2f}%")
        
        print(f"\nPer-test results:")
        for r in successful:
            print(f"  {r['input_file']:40s} RMSD: {r['rmsd']:8.4f}  Accuracy: {r['accuracy']:6.2f}%")
    
    if failed:
        print(f"\nFailed evaluations: {len(failed)}")
        for r in failed:
            print(f"  {r['input_file']:40s} ERROR: {r['error']}")


if __name__ == '__main__':
    main()

