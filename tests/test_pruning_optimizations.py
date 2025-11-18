"""Test script to compare synthesis with and without pruning optimizations.

This script runs synthesis on test examples with optimizations enabled/disabled
and compares RMSD scores and latencies.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import operator

import sympy as sym

from cse291p.pipeline.input import load_from_file
from cse291p.pipeline.view.loader import ViewLoader
from cse291p.pipeline.run import synthesize
from cse291p.pipeline.constraint.constraint import LinearConstraint, ConstantConstraint
from cse291p.pipeline.constraint.types import ConstraintKind
from cse291p.pipeline.view.types import AnchorID
from cse291p.pipeline.view.primitives import Attribute
from cse291p.evaluation import evaluate_layouts


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


def test_with_options(input_file: Path, options: Dict[str, Any]) -> Dict[str, Any]:
    """Run synthesis with given options and return results."""
    with input_file.open('r') as f:
        input_data = json.load(f)
    
    # Detect input format
    if 'train' in input_data:
        options['input_format'] = 'bench'
    else:
        options['input_format'] = 'default'
    
    result = synthesize(input_data, options)
    
    # Convert constraints to IConstraint objects for evaluation
    constraints = [dict_to_constraint(c) for c in result.get('constraints', [])]
    
    # Load examples as views for evaluation
    loader = ViewLoader(number_type=sym.Rational, input_format=options.get('input_format', 'default'))
    if options.get('input_format') == 'bench':
        examples_data = input_data.get('train', [])
    else:
        examples_data = input_data.get('examples', [])
    examples = [loader.load_dict(ex) for ex in examples_data]
    
    # Evaluate
    eval_result = evaluate_layouts(examples, constraints, conditional=False)
    
    return {
        'rmsd': eval_result.get('rmsd', float('inf')),
        'accuracy': eval_result.get('accuracy', 0.0),
        'num_constraints': len(constraints),
        'timings': result.get('timings', {}),
        'num_examples': len(examples)
    }


def compare_optimizations(input_file: Path) -> Dict[str, Any]:
    """Compare synthesis with and without optimizations."""
    print(f"\n{'='*80}")
    print(f"Testing: {input_file.name}")
    print('='*80)
    
    # Detect input format from file
    with input_file.open('r') as f:
        input_data = json.load(f)
    input_format = 'bench' if 'train' in input_data else 'default'
    
    base_options = {
        'input_format': input_format,
        'numeric_type': 'N',
        'instantiation_method': 'numpy',
        'learning_method': 'noisetolerant',
        'unambig': False,
        'pruning_method': 'hierarchical',
    }
    
    # Test 1: Without optimizations
    print("\n1. Running WITHOUT optimizations...")
    options_no_opt = base_options.copy()
    options_no_opt.update({
        'prune_axiom_violators': False,
        'enable_hierarchical_pruning': False,
        'enable_early_rejection': False,
    })
    result_no_opt = test_with_options(input_file, options_no_opt)
    
    # Test 2: With optimizations
    print("2. Running WITH optimizations...")
    options_with_opt = base_options.copy()
    options_with_opt.update({
        'prune_axiom_violators': True,
        'enable_hierarchical_pruning': True,
        'enable_early_rejection': True,
    })
    result_with_opt = test_with_options(input_file, options_with_opt)
    
    # Compare results
    comparison = {
        'input_file': input_file.name,
        'without_optimizations': result_no_opt,
        'with_optimizations': result_with_opt,
        'improvements': {
            'rmsd_change': result_with_opt['rmsd'] - result_no_opt['rmsd'],
            'rmsd_change_pct': ((result_with_opt['rmsd'] - result_no_opt['rmsd']) / result_no_opt['rmsd'] * 100) if result_no_opt['rmsd'] > 0 else 0,
            'accuracy_change': result_with_opt['accuracy'] - result_no_opt['accuracy'],
            'accuracy_change_pct': result_with_opt['accuracy'] - result_no_opt['accuracy'],
            'e2e_speedup': result_no_opt['timings'].get('e2e_latency_seconds', 0) / result_with_opt['timings'].get('e2e_latency_seconds', 1) if result_with_opt['timings'].get('e2e_latency_seconds', 0) > 0 else 0,
            'local_speedup': result_no_opt['timings'].get('local_inference_latency_seconds', 0) / result_with_opt['timings'].get('local_inference_latency_seconds', 1) if result_with_opt['timings'].get('local_inference_latency_seconds', 0) > 0 else 0,
            'global_speedup': result_no_opt['timings'].get('global_inference_latency_seconds', 0) / result_with_opt['timings'].get('global_inference_latency_seconds', 1) if result_with_opt['timings'].get('global_inference_latency_seconds', 0) > 0 else 0,
            'constraint_count_change': result_with_opt['num_constraints'] - result_no_opt['num_constraints'],
        }
    }
    
    # Print comparison
    print("\n" + "="*80)
    print("COMPARISON RESULTS")
    print("="*80)
    print(f"\nRMSD:")
    print(f"  Without optimizations: {result_no_opt['rmsd']:.4f}")
    print(f"  With optimizations:    {result_with_opt['rmsd']:.4f}")
    print(f"  Change:                {comparison['improvements']['rmsd_change']:+.4f} ({comparison['improvements']['rmsd_change_pct']:+.2f}%)")
    
    print(f"\nAccuracy:")
    print(f"  Without optimizations: {result_no_opt['accuracy']:.2f}%")
    print(f"  With optimizations:    {result_with_opt['accuracy']:.2f}%")
    print(f"  Change:                {comparison['improvements']['accuracy_change']:+.2f}%")
    
    print(f"\nLatency (seconds):")
    print(f"  E2E:")
    print(f"    Without optimizations: {result_no_opt['timings'].get('e2e_latency_seconds', 0):.3f}s")
    print(f"    With optimizations:    {result_with_opt['timings'].get('e2e_latency_seconds', 0):.3f}s")
    print(f"    Speedup:               {comparison['improvements']['e2e_speedup']:.2f}x")
    
    # Show breakdown
    input_no = result_no_opt['timings'].get('input_loading_latency_seconds', 0)
    sketch_no = result_no_opt['timings'].get('sketch_generation_latency_seconds', 0)
    local_no = result_no_opt['timings'].get('local_inference_latency_seconds', 0)
    global_no = result_no_opt['timings'].get('global_inference_latency_seconds', 0)
    format_no = result_no_opt['timings'].get('result_formatting_latency_seconds', 0)
    overhead_no = result_no_opt['timings'].get('overhead_latency_seconds', 0)
    
    input_opt = result_with_opt['timings'].get('input_loading_latency_seconds', 0)
    sketch_opt = result_with_opt['timings'].get('sketch_generation_latency_seconds', 0)
    local_opt = result_with_opt['timings'].get('local_inference_latency_seconds', 0)
    global_opt = result_with_opt['timings'].get('global_inference_latency_seconds', 0)
    format_opt = result_with_opt['timings'].get('result_formatting_latency_seconds', 0)
    overhead_opt = result_with_opt['timings'].get('overhead_latency_seconds', 0)
    
    e2e_no = result_no_opt['timings'].get('e2e_latency_seconds', 0)
    e2e_opt = result_with_opt['timings'].get('e2e_latency_seconds', 0)
    
    print(f"\n  Breakdown (without optimizations):")
    print(f"    Input loading:         {input_no:.3f}s ({input_no/e2e_no*100:.1f}%)")
    print(f"    Sketch generation:     {sketch_no:.3f}s ({sketch_no/e2e_no*100:.1f}%)")
    print(f"    Local inference:       {local_no:.3f}s ({local_no/e2e_no*100:.1f}%)")
    print(f"    Global inference:      {global_no:.3f}s ({global_no/e2e_no*100:.1f}%)")
    print(f"    Result formatting:     {format_no:.3f}s ({format_no/e2e_no*100:.1f}%)")
    print(f"    Overhead:              {overhead_no:.3f}s ({overhead_no/e2e_no*100:.1f}%)")
    
    print(f"\n  Breakdown (with optimizations):")
    print(f"    Input loading:         {input_opt:.3f}s ({input_opt/e2e_opt*100:.1f}%)")
    print(f"    Sketch generation:     {sketch_opt:.3f}s ({sketch_opt/e2e_opt*100:.1f}%)")
    print(f"    Local inference:       {local_opt:.3f}s ({local_opt/e2e_opt*100:.1f}%)")
    print(f"    Global inference:      {global_opt:.3f}s ({global_opt/e2e_opt*100:.1f}%)")
    print(f"    Result formatting:     {format_opt:.3f}s ({format_opt/e2e_opt*100:.1f}%)")
    print(f"    Overhead:              {overhead_opt:.3f}s ({overhead_opt/e2e_opt*100:.1f}%)")
    
    print(f"\n  Speedups by stage:")
    print(f"    Local Inference:       {comparison['improvements']['local_speedup']:.2f}x")
    print(f"    Global Inference:      {comparison['improvements']['global_speedup']:.2f}x")
    print(f"    (Other stages not optimized)")
    
    print(f"\nConstraints:")
    print(f"  Without optimizations: {result_no_opt['num_constraints']}")
    print(f"  With optimizations:    {result_with_opt['num_constraints']}")
    print(f"  Change:                {comparison['improvements']['constraint_count_change']:+d}")
    
    return comparison


def main():
    """Run comparison tests on test examples."""
    # Find test input files
    test_dir = Path(__file__).parent.parent / "tests" / "inputs"
    if not test_dir.exists():
        print(f"Test directory not found: {test_dir}")
        sys.exit(1)
    
    input_files = sorted(test_dir.glob("*.json"))
    
    if not input_files:
        print(f"No test input files found in {test_dir}")
        sys.exit(1)
    
    print(f"Found {len(input_files)} test input file(s)")
    print(f"Files: {[f.name for f in input_files]}")
    print("\nNote: This will run synthesis twice per file (with/without optimizations)")
    print("Starting comparison...\n")
    
    # Test each file
    results = []
    for input_file in input_files:
        try:
            comparison = compare_optimizations(input_file)
            results.append(comparison)
        except Exception as e:
            print(f"\n✗ Error testing {input_file.name}: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'input_file': input_file.name,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    successful = [r for r in results if 'error' not in r]
    if not successful:
        print("No successful comparisons")
        return
    
    # Aggregate statistics
    avg_rmsd_change = sum(r['improvements']['rmsd_change'] for r in successful) / len(successful)
    avg_accuracy_change = sum(r['improvements']['accuracy_change'] for r in successful) / len(successful)
    avg_e2e_speedup = sum(r['improvements']['e2e_speedup'] for r in successful) / len(successful)
    avg_local_speedup = sum(r['improvements']['local_speedup'] for r in successful) / len(successful)
    avg_global_speedup = sum(r['improvements']['global_speedup'] for r in successful) / len(successful)
    
    print(f"\nSuccessful comparisons: {len(successful)}/{len(results)}")
    print(f"\nAverage Improvements:")
    print(f"  RMSD change:        {avg_rmsd_change:+.4f} pixels")
    print(f"  Accuracy change:    {avg_accuracy_change:+.2f}%")
    print(f"  E2E speedup:        {avg_e2e_speedup:.2f}x")
    print(f"  Local speedup:      {avg_local_speedup:.2f}x")
    print(f"  Global speedup:     {avg_global_speedup:.2f}x")
    
    # Save results
    output_file = Path(__file__).parent / "pruning_optimization_results.json"
    with output_file.open('w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()

