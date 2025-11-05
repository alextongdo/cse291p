#!/usr/bin/env python3
"""Script to run all test inputs on both implementations and compare outputs."""

import json
import sys
import importlib
from pathlib import Path

# Clear Python cache to ensure fresh imports
import sys as _sys
if 'mockdown' in _sys.modules:
    # Force reload of mockdown modules
    modules_to_remove = [k for k in _sys.modules.keys() if k.startswith('mockdown')]
    for mod in modules_to_remove:
        del _sys.modules[mod]

# Clear __pycache__ directories
import shutil
for path in [Path(__file__).parent.parent / "mockdown" / "src", Path(__file__).parent.parent / "src"]:
    for cache_dir in path.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir, ignore_errors=True)

# Add both source directories to path
# ALWAYS use mockdown from cse291p/mockdown directory (local subdirectory)
CSE291P_ROOT = Path(__file__).parent.parent  # tests/ -> cse291p/
MOCKDOWN_LOCAL = CSE291P_ROOT / "mockdown" / "src"
MOCKDOWN_ORIGINAL = Path("/Users/xurui/Downloads/FA25/mockdown/src")
CSE291P_SRC = CSE291P_ROOT / "src"

# Verify local mockdown exists
if not MOCKDOWN_LOCAL.exists():
    raise FileNotFoundError(f"Local mockdown not found at: {MOCKDOWN_LOCAL}")
if not (MOCKDOWN_LOCAL / "mockdown" / "run.py").exists():
    raise FileNotFoundError(f"mockdown/run.py not found at: {MOCKDOWN_LOCAL / 'mockdown' / 'run.py'}")

print(f"✓ Using LOCAL mockdown at: {MOCKDOWN_LOCAL.resolve()}")
sys.path.insert(0, str(MOCKDOWN_LOCAL.resolve()))  # Add mockdown/src to path (for mockdown.* imports)
sys.path.insert(0, str(CSE291P_SRC.resolve()))

# Try to import mockdown.run, but handle Prolog dependency gracefully
try:
    # Force fresh import by removing from cache if present
    if 'mockdown.run' in sys.modules:
        del sys.modules['mockdown.run']
    if 'mockdown' in sys.modules:
        del sys.modules['mockdown']
    
    from mockdown.run import run as mockdown_run
    # Force reload to ensure latest code
    importlib.reload(sys.modules['mockdown.run'])
    from mockdown.run import run as mockdown_run
    MOCKDOWN_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    # Prolog dependencies might not be available
    if 'pyswip' in str(e) or 'SWI-Prolog' in str(e) or 'Prolog' in str(e):
        print("Warning: mockdown Prolog dependencies not available. Original implementation will be skipped.")
        MOCKDOWN_AVAILABLE = False
        mockdown_run = None
    else:
        raise

# Also reload cse291p modules to ensure fresh imports
if 'cse291p.pipeline.run' in sys.modules:
    importlib.reload(sys.modules['cse291p.pipeline.run'])
from cse291p.pipeline.run import synthesize
from cse291p.pipeline.output.read_output import format_constraint, parse_output


def run_original(input_file: Path, output_file: Path) -> dict:
    """Run original mockdown implementation."""
    if not MOCKDOWN_AVAILABLE:
        error_result = {'error': 'Mockdown not available (Prolog dependencies missing)'}
        with output_file.open('w') as f:
            json.dump(error_result, f, indent=2)
        return error_result
    
    try:
        # Force fresh import for each run
        import importlib
        if 'mockdown.run' in sys.modules:
            importlib.reload(sys.modules['mockdown.run'])
        from mockdown.run import run as mockdown_run
        
        with input_file.open('r') as f:
            input_data = json.load(f)
        
        options = {
            'input_format': 'default',
            'numeric_type': 'N',
            'instantiation_method': 'numpy',
            'learning_method': 'noisetolerant',
            'pruning_method': 'baseline',  # maps to BlackBoxPruner
            'debug_noise': 0,
            'unambig': False,
        }
        
        result = mockdown_run(input_data, options)
        if result is None:
            return {'error': 'Mockdown run returned None'}
        
        with output_file.open('w') as f:
            json.dump(result, f, indent=2)
        
        return result
    except Exception as e:
        import traceback
        error_result = {'error': str(e), 'traceback': str(e.__class__.__name__), 'full_traceback': traceback.format_exc()}
        with output_file.open('w') as f:
            json.dump(error_result, f, indent=2)
        return error_result


def run_refactored(input_file: Path, output_file: Path) -> dict:
    """Run refactored cse291p implementation."""
    try:
        with input_file.open('r') as f:
            input_data = json.load(f)
        
        options = {
            'input_format': 'default',
            'numeric_type': 'N',
            'instantiation_method': 'numpy',
            'learning_method': 'noisetolerant',
            'pruning_method': 'baseline',  # Use baseline for comparison
            'unambig': False,
        }
        
        result = synthesize(input_data, options)
        
        with output_file.open('w') as f:
            json.dump(result, f, indent=2)
        
        return result
    except Exception as e:
        error_result = {'error': str(e), 'traceback': str(e.__class__.__name__)}
        with output_file.open('w') as f:
            json.dump(error_result, f, indent=2)
        return error_result


def compare_outputs(original: dict, refactored: dict, comparison_file: Path):
    """Compare outputs and write comparison."""
    with comparison_file.open('w') as f:
        f.write("=== ORIGINAL OUTPUT ===\n")
        f.write(json.dumps(original, indent=2))
        f.write("\n\n")
        
        f.write("=== REFACTORED OUTPUT ===\n")
        f.write(json.dumps(refactored, indent=2))
        f.write("\n\n")
        
        f.write("=== COMPARISON ===\n")
        
        # Compare constraints
        orig_constraints = original.get('constraints', [])
        ref_constraints = refactored.get('constraints', [])
        
        f.write(f"Original constraints: {len(orig_constraints)}\n")
        f.write(f"Refactored constraints: {len(ref_constraints)}\n")
        f.write(f"Difference: {len(ref_constraints) - len(orig_constraints)}\n\n")
        
        # Compare constraint sets (by y_id and op)
        orig_set = {(c['y'], c.get('op', '=')) for c in orig_constraints}
        ref_set = {(c['y'], c.get('op', '=')) for c in ref_constraints}
        
        missing = orig_set - ref_set
        extra = ref_set - orig_set
        
        if missing:
            f.write(f"Missing constraints: {missing}\n")
        if extra:
            f.write(f"Extra constraints: {extra}\n")
        if not missing and not extra:
            f.write("✓ Constraint sets match!\n")


def main():
    """Main function to run all test inputs."""
    input_dir = Path(__file__).parent / "inputs"
    original_output_dir = Path(__file__).parent / "outputs" / "original"
    refactored_output_dir = Path(__file__).parent / "outputs" / "refactored"
    comparison_dir = Path(__file__).parent / "outputs" / "comparison"
    
    # Create output directories
    original_output_dir.mkdir(parents=True, exist_ok=True)
    refactored_output_dir.mkdir(parents=True, exist_ok=True)
    comparison_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Running all test inputs on both implementations")
    print("=" * 60)
    print()
    
    input_files = sorted(input_dir.glob("*.json"))
    
    for input_file in input_files:
        input_name = input_file.stem
        print(f"Processing: {input_name}")
        
        original_output = original_output_dir / f"{input_name}.json"
        refactored_output = refactored_output_dir / f"{input_name}.json"
        comparison_output = comparison_dir / f"{input_name}.txt"
        
        try:
            # Run original
            print(f"  Running original mockdown...")
            original_result = run_original(input_file, original_output)
            
            # Run refactored
            print(f"  Running refactored cse291p...")
            refactored_result = run_refactored(input_file, refactored_output)
            
            # Compare
            print(f"  Comparing outputs...")
            compare_outputs(original_result, refactored_result, comparison_output)
            
            print(f"  ✓ Completed {input_name}")
            
        except Exception as e:
            print(f"  ✗ Error processing {input_name}: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)
    print()
    print(f"Results saved in:")
    print(f"  Original outputs: {original_output_dir}")
    print(f"  Refactored outputs: {refactored_output_dir}")
    print(f"  Comparisons: {comparison_dir}")


if __name__ == '__main__':
    main()

