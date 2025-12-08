#!/usr/bin/env python3
"""
Compare original Mockdown vs new conditional pipeline on scraped datasets.

Usage:
    uv run python3 compare_rich.py [--filter SUBSTR]

Will scan data/generated/*_mockdown.json, run:
  - original Mockdown (mockdown.cli run)
  - new pipeline (src.run.synthesize equivalent via Conditional pipeline stack)

Outputs results to tmp/compare_rich_results.json and prints a summary.
"""

import json
import subprocess
import sys
import time
import logging as std_logging
from pathlib import Path
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader, module_from_spec

project_root = Path(__file__).parent
data_dir = project_root / "data" / "generated"
tmp_dir = project_root / "tmp"
tmp_dir.mkdir(exist_ok=True)

# Ensure stdlib logging is used (avoid shadowing by src/logging.py)
sys.modules["logging"] = std_logging

# Ensure imports from src/ (append after stdlib resolution)
sys.path.append(str(project_root / "src"))


def _load_module(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(loader.name, loader)
    module = module_from_spec(spec)
    loader.exec_module(module)
    sys.modules[name] = module
    return module


from evaluation import calculate_rmsd
from instantiation import ConditionalTemplateInstantiator
from learning import ConditionalBayesianLearning
from pruning import ConditionalHierarchicalPruner
from src.logging import setup_logging  # ensures logging config

util_loader = _load_module(
    "util_loader", project_root / "src" / "cse291p" / "util" / "loader.py"
)
load_examples_from_json = util_loader.load_examples_from_json


def list_datasets(filter_substr=None):
    files = sorted(data_dir.glob("*_mockdown.json"))
    if filter_substr:
        files = [f for f in files if filter_substr in f.name]
    return files


def run_mockdown(input_file: Path, output_file: Path):
    cmd = [
        "uv",
        "run",
        "python3",
        "-m",
        "mockdown.cli",
        "run",
        str(input_file),
        str(output_file),
        "--pruning-method",
        "none",
    ]
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_root / "mockdown"),
            capture_output=True,
            text=True,
            timeout=600,
        )
        elapsed = time.time() - start
        if result.returncode == 0 and output_file.exists():
            data = json.loads(output_file.read_text())
            num_constraints = len(data.get("constraints", []))
            return {"success": True, "time": elapsed, "constraints": num_constraints}
        else:
            return {
                "success": False,
                "time": elapsed,
                "error": result.stderr or result.stdout,
            }
    except Exception as e:
        return {"success": False, "time": None, "error": str(e)}


def run_new_pipeline(input_file: Path):
    start = time.time()
    try:
        views = load_examples_from_json(input_file)
        setup_logging(debug=False)
        # 1) instantiation
        example_idxs_to_templates_map = ConditionalTemplateInstantiator(
            examples=views
        ).instantiate()
        # 2) learning
        example_idxs_to_constrs_map = ConditionalBayesianLearning(
            examples=views, seed=42
        ).learn(example_idxs_to_templates_map)
        # 3) pruning
        out = ConditionalHierarchicalPruner(examples=views).prune(
            example_idxs_to_constrs_map
        )
        elapsed = time.time() - start
        rmsd = calculate_rmsd(views, out)
        num_constraints = sum(len(v) for v in out.values())
        return {
            "success": True,
            "time": elapsed,
            "constraints": num_constraints,
            "rmsd": rmsd,
        }
    except Exception as e:
        return {"success": False, "time": None, "error": str(e)}


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--filter", help="Substring to filter dataset names", default=None)
    args = parser.parse_args()

    files = list_datasets(args.filter)
    if not files:
        print("No datasets found")
        return 1

    results = []
    for f in files:
        name = f.stem.replace("_mockdown", "")
        print(f"\n=== {name} ===")

        mockdown_out = tmp_dir / f"mockdown_out_{name}.json"
        md_res = run_mockdown(f, mockdown_out)
        print("  Mockdown:", md_res)

        new_res = run_new_pipeline(f)
        print("  New pipeline:", new_res)

        results.append({"name": name, "mockdown": md_res, "new": new_res})

    out_path = tmp_dir / "compare_rich_results.json"
    out_path.write_text(json.dumps({"results": results}, indent=2))
    print(f"\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

