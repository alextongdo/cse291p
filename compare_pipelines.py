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
from collections import defaultdict

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
from src.config import ConditionalLearningConfig
import os
from src.pruning import ConditionalHierarchicalPruner
from src.types import View, LinearConstraint
from src.main import _solve_layout


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


def _view_to_dict(v: View) -> dict:
    return {
        "name": v.name,
        "rect": list(v.rect),
        "children": [_view_to_dict(c) for c in v.children],
    }


def _filter_dict_to_common_names(d: dict, common: set[str], keep_root: bool = False):
    name = d.get("name")
    children = d.get("children", [])
    filtered_children = []
    for c in children:
        fc = _filter_dict_to_common_names(c, common, keep_root=False)
        if fc is not None:
            filtered_children.append(fc)
    if keep_root or name in common:
        nd = dict(d)
        nd["children"] = filtered_children
        return nd
    if filtered_children:
        nd = dict(d)
        nd["children"] = filtered_children
        return nd
    return None


def align_views_to_union(views: list[View]) -> list[View]:
    """
    Pad missing view names across all examples to satisfy name consistency checks.
    Pads with rect=0 and tracks padded names for later RMSD masking.
    """
    if not views:
        return views
    union_names: set[str] = set()
    for ex in views:
        union_names.update(v.name for v in ex._flattened_views_in_subtree)
    aligned: list[View] = []
    for ex in views:
        present = {v.name for v in ex._flattened_views_in_subtree}
        missing = union_names - present
        if missing:
            for name in missing:
                ex.children.append(View(name=name, rect=(0, 0, 0, 0), children=[]))
            ex.model_post_init(None)
        setattr(ex, "_padded_names", missing)
        aligned.append(ex)
    return aligned


def rmsd_conditional_breakdown(
    examples: list[View], outputs: dict[tuple[int, ...], list[LinearConstraint]]
) -> tuple[float, list[float]]:
    """
    Compute per-example RMSD (and average) for conditional outputs by selecting constraints per example:
    - global constraints: key = tuple(range(len(examples)))
    - group-specific: pick the smallest group that contains the example.
      If a specific group is found, prefer it over global to avoid mixing
      incompatible branches (e.g., stacked mobile vs desktop grid).
    """
    n = len(examples)
    # per-category only selection
    def _category(view: View) -> str:
        w = view.width
        if w >= 1100:
            return "desktop"
        if w >= 700:
            return "tablet"
        return "mobile"

    categories = {idx: _category(v) for idx, v in enumerate(examples)}
    target_for = {idx: categories[idx] for idx in range(n)}

    skip_global = True
    global_key = tuple(range(n))
    global_constr: list[LinearConstraint] = []

    per_example_errors: list[float] = []

    for idx, ex in enumerate(examples):
        # pick most specific group containing idx; if none, fall back to global.
        candidate: list[tuple[int, tuple[int, ...], list[LinearConstraint]]] = []
        for k, v in outputs.items():
            if idx not in k:
                continue
            if len(k) == n:  # global
                continue
            cats = {categories[i] for i in k}
            if len(cats) != 1:
                continue
            if categories[idx] not in cats:
                continue
            candidate.append((len(k), k, v))
        if candidate:
            # prefer the largest applicable group to avoid underfit tiny subsets
            candidate.sort(key=lambda x: -x[0])
            _, _, constrs = candidate[0]
        else:
            constrs = global_constr
        if not constrs:
            continue

        solved = _solve_layout(ex, constrs, ex.width, ex.height)
        padded = getattr(ex, "_padded_names", set())
        predicted = {}
        for v in ex._flattened_views_in_subtree:
            if v.name in padded:
                continue
            predicted[v.name] = (
                solved[f"{v.name}.left"],
                solved[f"{v.name}.top"],
                solved[f"{v.name}.right"],
                solved[f"{v.name}.bottom"],
            )
        per_example_errors.append(calculate_rmsd(predicted, ex))

    avg = sum(per_example_errors) / len(per_example_errors) if per_example_errors else 0.0
    return avg, per_example_errors


def rmsd_conditional(examples: list[View], outputs: dict[tuple[int, ...], list[LinearConstraint]]) -> float:
    avg, _ = rmsd_conditional_breakdown(examples, outputs)
    return avg


def accuracy_conditional(examples: list[View], outputs: dict[tuple[int, ...], list[LinearConstraint]], tol: float = 1.0) -> float:
    """Compute accuracy: fraction of views whose rect matches within tol on all sides."""
    n = len(examples)
    # per-category only selection
    def _category(view: View) -> str:
        w = view.width
        if w >= 1100:
            return "desktop"
        if w >= 700:
            return "tablet"
        return "mobile"

    categories = {idx: _category(v) for idx, v in enumerate(examples)}

    skip_global = True
    global_key = tuple(range(n))
    global_constr: list[LinearConstraint] = []
    accuracies = []
    for idx, ex in enumerate(examples):
        group_constr = []
        candidate: list[tuple[int, tuple[int, ...], list[LinearConstraint]]] = []
        for k, v in outputs.items():
            if idx not in k:
                continue
            if len(k) == n:  # global
                continue
            cats = {categories[i] for i in k}
            if len(cats) != 1:
                continue
            if categories[idx] not in cats:
                continue
            candidate.append((len(k), k, v))
        if candidate:
            # prefer the largest applicable group to avoid underfit tiny subsets
            candidate.sort(key=lambda x: -x[0])
            _, _, group_constr = candidate[0]
        constrs = global_constr + group_constr
        if not constrs:
            continue
        solved = _solve_layout(ex, constrs, ex.width, ex.height)
        padded = getattr(ex, "_padded_names", set())
        total = 0
        correct = 0
        for v in ex._flattened_views_in_subtree:
            if v.name in padded:
                continue
            total += 1
            pl, pt, pr, pb = (
                solved[f"{v.name}.left"],
                solved[f"{v.name}.top"],
                solved[f"{v.name}.right"],
                solved[f"{v.name}.bottom"],
            )
            if (
                abs(pl - v.left) <= tol
                and abs(pt - v.top) <= tol
                and abs(pr - v.right) <= tol
                and abs(pb - v.bottom) <= tol
            ):
                correct += 1
        if total:
            accuracies.append(correct / total)
    if not accuracies:
        return 0.0
    return sum(accuracies) / len(accuracies)


def run_new_pipeline(examples_file: Path) -> dict:
    """
    Run new conditional pipeline and return results.
    
    Returns dict with: success, rmsd, num_constraints, total_time, stage_timings
    """
    print("\n" + "=" * 80)
    print("RUNNING NEW PIPELINE (Conditional Mockdown)")
    print("=" * 80)
    
    views = load_examples_legacy(examples_file)
    views = align_views_to_union(views)
    print(f"Loaded {len(views)} examples")

    # Heuristic viewport categories for optional biasing
    def _category(view: View) -> str:
        w = view.width
        if w >= 1100:
            return "desktop"
        if w >= 700:
            return "tablet"
        return "mobile"

    categories = {idx: _category(v) for idx, v in enumerate(views)}
    
    overall_start = time.perf_counter()
    
    # Stage 1: Template instantiation
    inst_start = time.perf_counter()
    example_idxs_to_templates_map = ConditionalTemplateInstantiator(
        examples=views
    ).instantiate()

    # Optional category bias: split template groups by inferred viewport category
    category_bias = os.getenv("CATEGORY_BIAS", "1").lower() in {"1", "true", "yes"}
    if category_bias:
        # Split mixed groups into per-category subsets; keep same-category groups as-is.
        filtered_map: dict[tuple[int, ...], list[LinearConstraint]] = defaultdict(list)
        for key, templates in example_idxs_to_templates_map.items():
            cat_to_idxs: dict[str, list[int]] = defaultdict(list)
            for idx in key:
                cat_to_idxs[categories[idx]].append(idx)
            for cat, idxs in cat_to_idxs.items():
                filtered_map[tuple(sorted(idxs))].extend(templates)

        # Add per-category global groups by uniting templates from that category.
        cat_to_idxs: dict[str, list[int]] = defaultdict(list)
        for idx, cat in categories.items():
            cat_to_idxs[cat].append(idx)
        for cat, idxs in cat_to_idxs.items():
            cat_key = tuple(sorted(idxs))
            collected: list[LinearConstraint] = []
            for key, templates in example_idxs_to_templates_map.items():
                if all(categories[i] == cat for i in key):
                    collected.extend(templates)
            if collected:
                filtered_map[cat_key].extend(collected)

        example_idxs_to_templates_map = dict(filtered_map)
    inst_time = time.perf_counter() - inst_start
    
    # Stage 2: Bayesian learning with clustering
    learn_start = time.perf_counter()
    max_dim = max(max(root.width, root.height) for root in views)
    a_thresh = float(os.getenv("A_THRESH", "0.05"))
    b_thresh = float(os.getenv("B_THRESH", "1.0"))
    conditional_config = ConditionalLearningConfig(
        max_offset=int(max_dim) + 10,
        a_cluster_threshold=a_thresh,
        b_cluster_threshold=b_thresh,
    )
    example_idxs_to_constrs_map = ConditionalBayesianLearning(
        examples=views,
        config=conditional_config,
        seed=42,
    ).learn(example_idxs_to_templates_map)

    # Optional post-learning constraint filtering: drop cross-dimension or high-ratio
    drop_cross = os.getenv("DROP_CROSS_DIM", "0").lower() in {"1", "true", "yes"}
    ratio_limit = float(os.getenv("RATIO_LIMIT", "0"))

    ignore_names_env = os.getenv("IGNORE_NAMES", "")
    ignore_names = {n.strip() for n in ignore_names_env.split(",") if n.strip()}

    def _filter_map(
        m: dict[tuple[int, ...], list[LinearConstraint]]
    ) -> dict[tuple[int, ...], list[LinearConstraint]]:
        if not drop_cross and ratio_limit <= 0 and not ignore_names:
            return m
        out: dict[tuple[int, ...], list[LinearConstraint]] = {}
        for k, cs in m.items():
            kept: list[LinearConstraint] = []
            for c in cs:
                if ignore_names:
                    if c.y.view.name in ignore_names or (
                        c.x is not None and c.x.view.name in ignore_names
                    ):
                        continue
                if c.x is not None:
                    if drop_cross and (c.y.is_horizontal() != c.x.is_horizontal()):
                        continue
                    if ratio_limit > 0 and c.a is not None:
                        a_val = float(c.a) if not isinstance(c.a, float) else c.a
                        if abs(a_val) > ratio_limit:
                            continue
                kept.append(c)
            out[k] = kept
        return out

    example_idxs_to_constrs_map = _filter_map(example_idxs_to_constrs_map)
    learn_time = time.perf_counter() - learn_start
    
    prune_strategy = os.getenv("PRUNE_STRATEGY", "hierarchical").lower()

    # Stage 3: Pruning (configurable)
    prune_start = time.perf_counter()
    if prune_strategy == "none":
        outputs = example_idxs_to_constrs_map
    else:
        try:
            outputs = ConditionalHierarchicalPruner(examples=views).prune(
                example_idxs_to_constrs_map
            )
        except Exception as e:
            print(f"[WARN] Hierarchical pruning failed ({e}); returning unpruned constraints")
            outputs = example_idxs_to_constrs_map
    prune_time = time.perf_counter() - prune_start
    
    overall_time = time.perf_counter() - overall_start
    
    # Calculate RMSD
    rmsd, rmsd_breakdown = rmsd_conditional_breakdown(views, outputs)
    acc = accuracy_conditional(views, outputs)
    num_constraints = sum(len(cs) for cs in outputs.values())
    
    print(f"✓ Completed in {overall_time:.4f}s")
    print(f"✓ Generated {num_constraints} constraints")
    print(f"  - Instantiation: {inst_time:.4f}s")
    print(f"  - Learning:      {learn_time:.4f}s")
    print(f"  - Pruning:       {prune_time:.4f}s")
    print(f"✓ RMSD: {rmsd:.4f} pixels")
    print(f"✓ ACC:  {acc:.4f}")
    print("  RMSD by example:", ", ".join(f"{e:.2f}" for e in rmsd_breakdown))
    
    return {
        'success': True,
        'rmsd': rmsd,
        'accuracy': acc,
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

