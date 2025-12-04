"""
Run the original Mockdown implementation on freshly scraped IEEE examples.

This script is analogous to `run_original_ieee.py`, but instead of reading
from `auto-mock/bench_cache/ieeexplore.json` it reads the JSON produced by
`src/cse291p/util/multi_viewport_scraper.py` at:

    src/cse291p/util/websites/ieeexplore.ieee.org/ieeexplore.ieee.org_scraped.json

It then:
  * converts the scraped view hierarchies into Mockdown's expected input
    format (rect = [left, top, right, bottom]),
  * runs `mockdown.run.run` using the same options as `run_original_mockdown.py`,
  * solves the resulting constraints with Kiwi to reconstruct layouts, and
  * computes RMSD between the reconstructed layouts and the scraped ground
    truth.

USAGE (from your local machine, with the original `fifteenAI` conda env):

    conda activate fifteenAI
    cd /Users/xurui/Downloads/FA25/cse291p
    python run_original_ieee_scraped.py

This will print timing, number of constraints, RMSD, and write a JSON report
to `original_ieee_results_scraped.json` in the project root.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List

import kiwisolver

# Add mockdown to path
import sys

MOCKDOWN_SRC = Path(__file__).parent / "mockdown" / "src"
if str(MOCKDOWN_SRC) not in sys.path:
    sys.path.insert(0, str(MOCKDOWN_SRC))

from mockdown.run import run as run_mockdown  # type: ignore[import]


def flatten_views(view_dict: Dict[str, Any], parent: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    """Flatten a nested view hierarchy into a list with parent pointers."""
    view = {
        "name": view_dict["name"],
        "rect": view_dict["rect"],
        "parent": parent,
        "children": [],
    }
    result = [view]
    for child in view_dict.get("children", []):
        child_views = flatten_views(child, view)
        # first element of child_views is the child's root
        view["children"].append(child_views[0])
        result.extend(child_views)
    return result


def solve_constraints(constraints: List[Dict[str, Any]], root_dict: Dict[str, Any]) -> Dict[str, float]:
    """Solve a set of Mockdown-style constraints with Kiwi for a single example.

    `constraints` is the list of constraint dicts from Mockdown's output.
    `root_dict` is a single example from the scraped JSON (with nested children).
    """
    solver = kiwisolver.Solver()

    # Flatten hierarchy and allocate variables
    all_views = flatten_views(root_dict)
    var_map: Dict[str, kiwisolver.Variable] = {}

    for view in all_views:
        for anchor_type in [
            "left",
            "right",
            "top",
            "bottom",
            "width",
            "height",
            "center_x",
            "center_y",
        ]:
            key = f"{view['name']}.{anchor_type}"
            var_map[key] = kiwisolver.Variable(key)

    # Add layout axioms
    for view in all_views:
        w = var_map[f"{view['name']}.width"]
        h = var_map[f"{view['name']}.height"]
        l = var_map[f"{view['name']}.left"]
        r = var_map[f"{view['name']}.right"]
        t = var_map[f"{view['name']}.top"]
        b = var_map[f"{view['name']}.bottom"]
        cx = var_map[f"{view['name']}.center_x"]
        cy = var_map[f"{view['name']}.center_y"]

        solver.addConstraint((w == r - l) | "required")
        solver.addConstraint((h == b - t) | "required")
        solver.addConstraint((cx == (l + r) / 2) | "required")
        solver.addConstraint((cy == (t + b) / 2) | "required")
        solver.addConstraint((w >= 0) | "required")
        solver.addConstraint((h >= 0) | "required")
        solver.addConstraint((l >= 0) | "required")
        solver.addConstraint((t >= 0) | "required")

    # Add synthesized constraints from Mockdown
    for c in constraints:
        y_name = c["y"]
        y_var = var_map[y_name]
        x_name = c.get("x")
        if x_name:
            x_var = var_map[x_name]
            a_raw = c.get("a", "1")
            if isinstance(a_raw, str):
                if "/" in a_raw:
                    num, den = map(float, a_raw.split("/"))
                    a = num / den
                else:
                    a = float(a_raw)
            else:
                a = float(a_raw)
            b = float(c.get("b", "0") or 0.0)
            solver.addConstraint((y_var == a * x_var + b) | "required")
        else:
            b = float(c.get("b", "0") or 0.0)
            solver.addConstraint((y_var == b) | "required")

    # Fix root dimensions and origin
    left, top, right, bottom = root_dict["rect"]
    width = float(right - left)
    height = float(bottom - top)
    root_name = root_dict["name"]
    solver.addConstraint((var_map[f"{root_name}.width"] == width) | "required")
    solver.addConstraint((var_map[f"{root_name}.height"] == height) | "required")
    solver.addConstraint((var_map[f"{root_name}.left"] == 0) | "required")
    solver.addConstraint((var_map[f"{root_name}.top"] == 0) | "required")

    solver.updateVariables()
    return {key: var.value() for key, var in var_map.items()}


def calculate_rmsd_for_mockdown(
    examples: List[Dict[str, Any]],
    constraints: List[Dict[str, Any]],
) -> float:
    """Compute RMSD between Mockdown's solved layouts and the scraped ground truth."""
    all_errors: List[float] = []

    for example in examples:
        try:
            solved = solve_constraints(constraints, example)

            # Flatten views to compare all anchors
            all_views = flatten_views(example)
            for view in all_views:
                left, top, right, bottom = view["rect"]
                width = right - left
                height = bottom - top
                center_x = (left + right) / 2
                center_y = (top + bottom) / 2

                for anchor_type, actual in [
                    ("left", left),
                    ("right", right),
                    ("top", top),
                    ("bottom", bottom),
                    ("width", width),
                    ("height", height),
                    ("center_x", center_x),
                    ("center_y", center_y),
                ]:
                    key = f"{view['name']}.{anchor_type}"
                    if key in solved:
                        error = solved[key] - float(actual)
                        all_errors.append(error * error)
        except Exception as exc:  # pragma: no cover - diagnostic only
            print(f"  Warning: failed to solve example {example.get('name')}: {exc}")
            continue

    if not all_errors:
        return 0.0

    mse = sum(all_errors) / len(all_errors)
    return math.sqrt(mse)


def main() -> None:
    # Load scraped IEEE examples produced by our scraper
    project_root = Path(__file__).parent
    scraped_path = project_root / "src" / "cse291p" / "util" / "websites" / "ieeexplore.ieee.org" / "ieeexplore.ieee.org_scraped.json"
    if not scraped_path.exists():
        raise SystemExit(f"Scraped IEEE file not found: {scraped_path}")

    with scraped_path.open() as f:
        scraped = json.load(f)

    raw_examples: List[Dict[str, Any]] = scraped.get("examples", [])
    if not raw_examples:
        raise SystemExit("No 'examples' found in scraped IEEE JSON")

    # Use the first few examples to keep runtime reasonable and comparable
    train_examples = raw_examples[:3]

    print("=" * 80)
    print("ORIGINAL MOCKDOWN ON SCRAPED IEEE DATASET")
    print("=" * 80)
    print(f"Using {len(train_examples)} training examples from {scraped.get('meta', {}).get('scrape', {}).get('origin', 'unknown source')}")

    # Build Mockdown input; the scraped rects are already [left, top, right, bottom]
    mockdown_input: Dict[str, Any] = {
        "examples": train_examples,
        "options": {
            "input_format": "default",
            "numeric_type": "N",
            "instantiation_method": "numpy",
            "learning_method": "noisetolerant",
            "pruning_method": "hierarchical",
            "pruning_bounds": (None, None, None, None),
            "include_axioms": False,
            "debug": False,
            "unambig": False,
        },
    }

    print("\nRunning original mockdown on scraped IEEE examples...")
    import time

    start = time.perf_counter()
    result = run_mockdown(input_data=mockdown_input, options=mockdown_input["options"])  # type: ignore[arg-type]
    elapsed = time.perf_counter() - start

    constraints: List[Dict[str, Any]] = result.get("constraints", [])
    print(f"  Time: {elapsed:.4f}s")
    print(f"  Constraints: {len(constraints)}")  # total constraints

    # Compute RMSD against the scraped ground truth
    rmsd = calculate_rmsd_for_mockdown(train_examples, constraints)
    print(f"  RMSD vs scraped layouts: {rmsd:.4f}")

    # Persist summary for later comparison
    summary = {
        "time": elapsed,
        "rmsd": rmsd,
        "constraints": len(constraints),
        "num_examples": len(train_examples),
        "source": str(scraped_path),
    }

    out_path = project_root / "original_ieee_results_scraped.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":  # pragma: no cover - manual entry point
    main()


