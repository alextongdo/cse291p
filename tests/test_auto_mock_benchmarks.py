"""Test evaluation metrics against auto-mock benchmark examples.

This script loads benchmark examples from auto-mock's bench_cache directory,
runs synthesis, and evaluates using our metrics to compare with auto-mock's results.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
import sys
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


def convert_auto_mock_to_our_format(auto_mock_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert auto-mock benchmark format to our input format.
    
    Auto-mock format:
    {
        "train": [{"name": "...", "top": ..., "left": ..., "height": ..., "width": ..., "children": [...]}],
        "test": [...]
    }
    
    Our format:
    {
        "examples": [{"name": "...", "rect": [left, top, right, bottom], "children": [...]}]
    }
    """
    def convert_view(view: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a single view from auto-mock format to our format."""
        left = view["left"]
        top = view["top"]
        width = view["width"]
        height = view["height"]
        
        # Convert LTWH to LTRB (left, top, right, bottom)
        right = left + width
        bottom = top + height
        
        result = {
            "name": view["name"],
            "rect": [left, top, right, bottom],
            "children": [convert_view(child) for child in view.get("children", [])]
        }
        return result
    
    # Convert train examples
    examples = [convert_view(view) for view in auto_mock_data.get("train", [])]
    
    return {"examples": examples}


def load_auto_mock_benchmark(bench_path: Path) -> Dict[str, Any]:
    """Load an auto-mock benchmark file."""
    with bench_path.open('r') as f:
        return json.load(f)


def test_benchmark(bench_path: Path, bench_name: str) -> Dict[str, Any]:
    """Test a single benchmark and return evaluation results."""
    print(f"\n{'='*60}")
    print(f"Testing: {bench_name}")
    print('='*60)
    
    try:
        # Load auto-mock benchmark
        auto_mock_data = load_auto_mock_benchmark(bench_path)
        
        # Check if it has train data
        if "train" not in auto_mock_data or not auto_mock_data["train"]:
            print(f"  ⚠️  No training data in {bench_name}")
            return {"name": bench_name, "error": "No training data"}
        
        # Convert to our format
        our_format = convert_auto_mock_to_our_format(auto_mock_data)
        num_examples = len(our_format["examples"])
        print(f"  Loaded {num_examples} training examples")
        
        # Run synthesis
        print("  Running synthesis (this may take a while)...")
        try:
            options = {
                'input_format': 'default',
                'numeric_type': 'N',
                'instantiation_method': 'numpy',
                'learning_method': 'noisetolerant',
                'unambig': False,
            }
            
            output = synthesize(our_format, options)
            constraints_dict = output.get('constraints', [])
            print(f"  Generated {len(constraints_dict)} constraints")
        except Exception as e:
            print(f"  ✗ Synthesis failed: {e}")
            import traceback
            traceback.print_exc()
            return {"name": bench_name, "error": f"Synthesis failed: {str(e)}"}
        
        # Convert constraint dictionaries to constraint objects
        constraints = [dict_to_constraint(c) for c in constraints_dict]
        
        # Load examples as views for evaluation
        loader = ViewLoader(number_type=sym.Rational, input_format='default')
        examples = [loader.load_dict(ex) for ex in our_format['examples']]
        
        # Evaluate
        print("  Evaluating metrics...")
        eval_result = evaluate_layouts(examples, constraints, conditional=False)
        
        # Print results
        print(f"  RMSD: {eval_result['rmsd']:.4f} pixels")
        print(f"  Accuracy: {eval_result['accuracy']:.2f}%")
        print(f"  Number of examples: {eval_result['num_examples']}")
        
        return {
            "name": bench_name,
            "num_examples": num_examples,
            "num_constraints": len(constraints),
            "rmsd": eval_result['rmsd'],
            "accuracy": eval_result['accuracy'],
            "per_example_rmsd": eval_result.get('per_example_rmsd', []),
            "per_example_accuracy": eval_result.get('per_example_accuracy', []),
        }
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"name": bench_name, "error": str(e)}


def main():
    """Run evaluation on auto-mock benchmarks."""
    # Path to auto-mock bench_cache
    auto_mock_dir = Path(__file__).parent.parent / "auto-mock" / "bench_cache"
    
    if not auto_mock_dir.exists():
        print(f"Error: auto-mock directory not found at {auto_mock_dir}")
        print("Make sure auto-mock/bench_cache exists with benchmark JSON files")
        sys.exit(1)
    
    # Get all benchmark JSON files
    benchmark_files = sorted(auto_mock_dir.glob("*.json"))
    
    # Filter out old directory
    benchmark_files = [f for f in benchmark_files if not f.name.startswith("old")]
    
    # Filter to only FWT benchmarks
    benchmark_files = [f for f in benchmark_files if f.stem.startswith("fwt-")]
    
    # Start with simpler FWT benchmarks (fewer views) for faster testing
    simple_fwt = ['fwt-main-logo', 'fwt-space-footer', 'fwt-space-header', 'fwt-content', 'fwt-footer']
    benchmark_files = [f for f in benchmark_files if f.stem in simple_fwt]
    
    if not benchmark_files:
        # Fallback: just use first 3 FWT benchmarks
        all_fwt = [f for f in sorted(auto_mock_dir.glob("fwt-*.json")) if not f.name.startswith("old")]
        benchmark_files = all_fwt[:3]
    
    if not benchmark_files:
        print(f"No FWT benchmark files found in {auto_mock_dir}")
        sys.exit(1)
    
    print(f"Testing {len(benchmark_files)} FWT benchmark file(s)")
    print(f"Benchmarks: {[f.stem for f in benchmark_files]}")
    print("\nNote: This will run synthesis on each benchmark, which may take time.")
    print("Starting evaluation...\n")
    
    # Test each benchmark
    results = []
    for bench_file in benchmark_files:
        bench_name = bench_file.stem
        result = test_benchmark(bench_file, bench_name)
        results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    
    successful = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]
    
    if successful:
        avg_rmsd = sum(r['rmsd'] for r in successful) / len(successful)
        avg_accuracy = sum(r['accuracy'] for r in successful) / len(successful)
        total_constraints = sum(r['num_constraints'] for r in successful)
        
        print(f"\nSuccessful evaluations: {len(successful)}/{len(results)}")
        print(f"Average RMSD: {avg_rmsd:.4f} pixels")
        print(f"Average Accuracy: {avg_accuracy:.2f}%")
        print(f"Total constraints generated: {total_constraints}")
        
        print(f"\nPer-benchmark results:")
        print(f"{'Benchmark':<40} {'Examples':<10} {'Constraints':<12} {'RMSD':<12} {'Accuracy':<10}")
        print("-" * 90)
        for r in successful:
            print(f"{r['name']:<40} {r['num_examples']:<10} {r['num_constraints']:<12} "
                  f"{r['rmsd']:<12.4f} {r['accuracy']:<10.2f}%")
    
    if failed:
        print(f"\nFailed evaluations: {len(failed)}")
        for r in failed:
            print(f"  {r['name']:<40} ERROR: {r['error']}")
    
    # Save results to JSON
    output_file = Path(__file__).parent / "auto_mock_benchmark_results.json"
    with output_file.open('w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()

