"""Simple test of evaluation metrics that doesn't require full pipeline.

This test uses pre-computed constraint dictionaries from output files
to test the evaluation metrics without running the full synthesis pipeline.
"""

import json
from pathlib import Path
from typing import Dict, Any

import sympy as sym

from cse291p.pipeline.view.loader import ViewLoader
from cse291p.pipeline.constraint import LinearConstraint, ConstantConstraint
from cse291p.pipeline.constraint.types import ConstraintKind
from cse291p.pipeline.view.types import AnchorID
from cse291p.pipeline.view.primitives import Attribute
from cse291p.evaluation import evaluate_layouts
import operator


def parse_anchor_id(anchor_str: str) -> AnchorID:
    """Parse anchor ID from string like 'child.width' or 'root.left'."""
    parts = anchor_str.split('.')
    if len(parts) != 2:
        raise ValueError(f"Invalid anchor format: {anchor_str}")
    view_name, attr_name = parts
    attr = Attribute[attr_name.upper()]
    return AnchorID(view_name=view_name, attribute=attr)


def dict_to_constraint(constraint_dict: Dict[str, str]):
    """Convert constraint dictionary to IConstraint object."""
    kind_str = constraint_dict['kind']
    # Map output format to enum name (handle variations like pos_lrtb_offset -> POS_LTRB_OFFSET)
    kind_str_upper = kind_str.upper()
    # Fix common typo: LRTB -> LTRB
    if 'LRTB' in kind_str_upper:
        kind_str_upper = kind_str_upper.replace('LRTB', 'LTRB')
    kind = ConstraintKind[kind_str_upper]
    
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
        return ConstantConstraint(
            kind=kind,
            y_id=y_id,
            b=b,
            op=op,
            sample_count=1
        )
    else:
        return LinearConstraint(
            kind=kind,
            y_id=y_id,
            x_id=x_id,
            a=a,
            b=b,
            op=op,
            sample_count=1
        )


def test_evaluation_with_output_file(input_file: Path, output_file: Path):
    """Test evaluation using pre-computed constraints from output file."""
    print(f"\n{'='*60}")
    print(f"Testing: {input_file.name}")
    print('='*60)
    
    # Load input examples
    with input_file.open('r') as f:
        input_data = json.load(f)
    
    loader = ViewLoader(number_type=sym.Rational, input_format='default')
    examples = [loader.load_dict(ex) for ex in input_data['examples']]
    print(f"Loaded {len(examples)} examples")
    
    # Load constraints from output file
    if not output_file.exists():
        print(f"Output file not found: {output_file}")
        return None
    
    with output_file.open('r') as f:
        output_data = json.load(f)
    
    constraints_dict = output_data.get('constraints', [])
    print(f"Loaded {len(constraints_dict)} constraints from output file")
    
    # Convert to constraint objects
    constraints = [dict_to_constraint(c) for c in constraints_dict]
    
    # Evaluate
    print("Evaluating metrics...")
    eval_result = evaluate_layouts(examples, constraints, conditional=False)
    
    # Print results
    print(f"\nResults:")
    print(f"  RMSD: {eval_result['rmsd']:.4f} pixels")
    print(f"  Accuracy: {eval_result['accuracy']:.2f}%")
    print(f"  Number of examples: {eval_result['num_examples']}")
    
    return {
        'input_file': input_file.name,
        'rmsd': eval_result['rmsd'],
        'accuracy': eval_result['accuracy'],
        'num_examples': eval_result['num_examples'],
        'num_constraints': len(constraints),
    }


def main():
    """Run evaluation on test cases using pre-computed outputs."""
    test_dir = Path(__file__).parent
    inputs_dir = test_dir / 'inputs'
    outputs_dir = test_dir / 'outputs' / 'refactored'
    
    # Get all test input files
    input_files = sorted(inputs_dir.glob('*.json'))
    
    if not input_files:
        print(f"No test files found in {inputs_dir}")
        return
    
    print(f"Found {len(input_files)} test cases")
    print("\nNote: This test uses pre-computed constraints from output files.")
    print("For full pipeline evaluation, use test_evaluation_on_examples.py")
    print("(requires fixing NumPy/pandas version compatibility)")
    
    results = []
    for input_file in input_files:
        output_file = outputs_dir / input_file.name
        try:
            result = test_evaluation_with_output_file(input_file, output_file)
            if result:
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

