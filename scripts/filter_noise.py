#!/usr/bin/env python3
"""
Filter scraped mockdown JSON to remove small/noisy elements while keeping
responsive structure. Heuristics:
- Keep root always.
- Keep children whose area >= area_threshold * root_area OR that are among the top_k largest in the example.
- Recursively filter children with the same rule (threshold relative to root).

Default: area_threshold=0.001 (0.1% of root area), top_k=40.

Usage:
  uv run python3 scripts/filter_noise.py input.json --out filtered.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def area(v: dict[str, Any]) -> float:
    l, t, r, b = v.get("rect", [0, 0, 0, 0])
    return max(0.0, r - l) * max(0.0, b - t)


def walk(v: dict[str, Any]) -> list[dict[str, Any]]:
    out = [v]
    for c in v.get("children", []) or []:
        out.extend(walk(c))
    return out


def filter_view(v: dict[str, Any], root_area: float, area_threshold: float, top_names: set[str]) -> dict[str, Any] | None:
    a = area(v)
    keep = v.get("name") in top_names or a >= area_threshold * root_area
    if not keep:
        return None
    children = []
    for c in v.get("children", []) or []:
        fc = filter_view(c, root_area, area_threshold, top_names)
        if fc:
            children.append(fc)
    nv = dict(v)
    nv["children"] = children
    return nv


def process_example(ex: dict[str, Any], area_threshold: float, top_k: int) -> dict[str, Any]:
    root = ex
    root_area = max(area(root), 1.0)
    all_views = walk(ex)
    # pick top_k names by area to force-keep
    top_sorted = sorted(all_views, key=area, reverse=True)[:top_k]
    top_names = {v.get("name") for v in top_sorted if v.get("name")}
    filtered = filter_view(root, root_area, area_threshold, top_names)
    return filtered or root


def load_examples(path: Path) -> list[dict[str, Any]]:
    data = json.load(open(path))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "examples" in data:
            return data["examples"]
        if "train" in data:
            return data["train"]
        vals = list(data.values())
        if len(vals) == 1 and isinstance(vals[0], list):
            return vals[0]
    raise ValueError(f"Unsupported format in {path}")


def save_examples(path: Path, examples: list[dict[str, Any]]) -> None:
    with open(path, "w") as f:
        json.dump({"examples": examples}, f, indent=2)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--area-threshold", type=float, default=0.001, help="fraction of root area")
    ap.add_argument("--top-k", type=int, default=40)
    args = ap.parse_args()

    examples = load_examples(args.input)
    filtered = [process_example(ex, args.area_threshold, args.top_k) for ex in examples]
    out_path = args.out or args.input
    save_examples(out_path, filtered)
    print(f"filtered {args.input} -> {out_path} (n={len(filtered)})")


if __name__ == "__main__":
    main()

