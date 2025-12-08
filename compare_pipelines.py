#!/usr/bin/env python3
"""
Compare the new conditional pipeline with original Mockdown.

Runs both pipelines on the same examples and outputs:
- RMSD (Root Mean Square Deviation) for layout accuracy
- Latency breakdown by pipeline stage
- Number of constraints generated

Usage:
    uv run python3 compare_pipelines.py [examples_file]

If no examples_file is provided, defaults to tmp/new_ieee_examples.json
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

# Fix path ordering to avoid shadowing stdlib modules (e.g., logging, types)
project_root = Path(__file__).parent
script_dir = project_root / 'src'

if sys.path and sys.path[0] == str(script_dir):
    sys.path.pop(0)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.evaluation import calculate_rmsd
from src.instantiation import ConditionalTemplateInstantiator
from src.learning import ConditionalBayesianLearning
from src.pruning import ConditionalHierarchicalPruner
from src.types import View


def load_examples_legacy(path: Path) -> list[View]:
    """
    Load examples from multiple possible formats:
    - {"examples": [...]} (new scraped format)
    - {"train": [...]} (legacy mockdown paper format)
    - raw list [...]
    """
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, list):
        examples = data
    elif isinstance(data, dict):
        if "examples" in data:
            examples = data["examples"]
        elif "train" in data:
            examples = data["train"]
        else:
            # fallback: maybe the dict itself is an example list keyed differently
            # try to interpret values as list if there's only one key
            if len(data.values()) == 1 and isinstance(list(data.values())[0], list):
                examples = list(data.values())[0]
            else:
                raise KeyError("Could not find examples or train keys in JSON file")
    else:
        raise ValueError("Unsupported JSON format for examples")

    def normalize_view(d: dict) -> dict:
        """
        Ensure rect exists; mirror original Mockdown tolerance:
        - If rect missing but left/top/width/height present, derive rect.
        - If neither present, default rect to [0,0,0,0].
        - Recurse into children.
        """
        v = dict(d)
        if "rect" not in v:
            if all(k in v for k in ("left", "top", "width", "height")):
                l, t, w, h = v["left"], v["top"], v["width"], v["height"]
                v["rect"] = [l, t, l + w, t + h]
            else:
                v["rect"] = [0, 0, 0, 0]
        if "children" in v and isinstance(v["children"], list):
            v["children"] = [normalize_view(c) for c in v["children"]]
        return v

    return [View(**normalize_view(ex)) for ex in examples]


def run_new_pipeline(examples_file: Path) -> dict:
    """
    Run new conditional pipeline and return results.
    
    Returns dict with: success, rmsd, num_constraints, total_time, stage_timings
    """
    print("\n" + "=" * 80)
    print("RUNNING NEW PIPELINE (Conditional Mockdown)")
    print("=" * 80)
    
    views = load_examples_legacy(examples_file)
    print(f"Loaded {len(views)} examples")
    
    overall_start = time.perf_counter()
    
    # Stage 1: Template instantiation
    inst_start = time.perf_counter()
    example_idxs_to_templates_map = ConditionalTemplateInstantiator(
        examples=views
    ).instantiate()
    inst_time = time.perf_counter() - inst_start
    
    # Stage 2: Bayesian learning with clustering
    learn_start = time.perf_counter()
    example_idxs_to_constrs_map = ConditionalBayesianLearning(
        examples=views, seed=42
    ).learn(example_idxs_to_templates_map)
    learn_time = time.perf_counter() - learn_start
    
    # Stage 3: Hierarchical pruning
    prune_start = time.perf_counter()
    outputs = ConditionalHierarchicalPruner(examples=views).prune(
        example_idxs_to_constrs_map
    )
    prune_time = time.perf_counter() - prune_start
    
    overall_time = time.perf_counter() - overall_start
    
    # Calculate RMSD
    rmsd = calculate_rmsd(views, outputs, debug=False)
    num_constraints = sum(len(cs) for cs in outputs.values())
    
    print(f"✓ Completed in {overall_time:.4f}s")
    print(f"✓ Generated {num_constraints} constraints")
    print(f"  - Instantiation: {inst_time:.4f}s")
    print(f"  - Learning:      {learn_time:.4f}s")
    print(f"  - Pruning:       {prune_time:.4f}s")
    print(f"✓ RMSD: {rmsd:.4f} pixels")
    
    return {
        'success': True,
        'rmsd': rmsd,
        'num_constraints': num_constraints,
        'total_time': overall_time,
        'stage_timings': {
            'instantiation': inst_time,
            'learning': learn_time,
            'pruning': prune_time,
        }
    }


def run_mockdown(examples_file: Path, output_file: Path) -> dict:
    """
    Run original Mockdown and return results.
    
    Tries pruning methods in order: none, baseline.
    Returns dict with: success, num_constraints, total_time, pruning_method, error
    """
    print("\n" + "=" * 80)
    print("RUNNING ORIGINAL MOCKDOWN")
    print("=" * 80)
    
    start_time = time.time()
    
    for pruning_method in ['none', 'baseline']:
        cmd = [
            'uv', 'run', 'python3', '-m', 'mockdown.cli', 'run',
            str(examples_file),
            str(output_file),
            '--pruning-method', pruning_method
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(project_root / 'mockdown'),
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0 and output_file.exists():
                total_time = time.time() - start_time
                
                with output_file.open() as f:
                    results = json.load(f)
                num_constraints = len(results.get('constraints', []))
                
                print(f"✓ Completed in {total_time:.4f}s (pruning: {pruning_method})")
                print(f"✓ Generated {num_constraints} constraints")
                
                return {
                    'success': True,
                    'num_constraints': num_constraints,
                    'total_time': total_time,
                    'pruning_method': pruning_method
                }
        except subprocess.TimeoutExpired:
            print(f"  Timeout with pruning={pruning_method}")
        except Exception as e:
            print(f"  Error with pruning={pruning_method}: {e}")
    
    print("✗ All pruning methods failed")
    return {'success': False, 'error': 'All pruning methods failed (non-isomorphic examples not supported)'}


def print_summary(pipeline_result: dict, mockdown_result: dict):
    """Print comparison summary."""
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
    print("\nNEW PIPELINE (Conditional Mockdown):")
    if pipeline_result['success']:
        print(f"  Constraints: {pipeline_result['num_constraints']}")
        print(f"  RMSD:        {pipeline_result['rmsd']:.4f} pixels")
        print(f"  Total time:  {pipeline_result['total_time']:.4f}s")
        print(f"  Stage timings:")
        for stage, duration in pipeline_result['stage_timings'].items():
            print(f"    {stage}: {duration:.4f}s")
    else:
        print(f"  Failed: {pipeline_result.get('error', 'Unknown error')}")
    
    print("\nORIGINAL MOCKDOWN:")
    if mockdown_result['success']:
        print(f"  Constraints: {mockdown_result['num_constraints']}")
        print(f"  Total time:  {mockdown_result['total_time']:.4f}s")
        print(f"  Pruning:     {mockdown_result.get('pruning_method', 'unknown')}")
    else:
        print(f"  Failed: {mockdown_result.get('error', 'Unknown error')}")
    
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='Compare new pipeline with original Mockdown')
    parser.add_argument('examples_file', nargs='?', 
                        default=str(project_root / 'tmp' / 'new_ieee_examples.json'),
                        help='Path to examples JSON file')
    args = parser.parse_args()
    
    examples_file = Path(args.examples_file)
    mockdown_output = project_root / 'tmp' / 'mockdown_results.json'
    
    if not examples_file.exists():
        print(f"Error: Examples file not found: {examples_file}")
        return 1
    
    pipeline_result = run_new_pipeline(examples_file)
    mockdown_result = run_mockdown(examples_file, mockdown_output)
    print_summary(pipeline_result, mockdown_result)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

