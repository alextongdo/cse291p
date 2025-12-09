#!/usr/bin/env python3
"""
Quick SVG visualizer for mockdown-style examples.

Inputs: JSON file with {"examples": [...]} or {"train": [...]} or a raw list.
Outputs: one SVG per example into the specified output directory.

Usage:
    uv run python3 scripts/visualize_examples.py data/generated/bbc_mockdown.json --out tmp/viz
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

MIN_SIZE = 1.0


def load_examples(path: Path) -> list[dict[str, Any]]:
    with path.open() as f:
        data = json.load(f)
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


def to_rect(v: dict[str, Any]) -> tuple[float, float, float, float]:
    if "rect" in v and isinstance(v["rect"], (list, tuple)) and len(v["rect"]) == 4:
        l, t, r, b = [float(x) for x in v["rect"]]
    elif all(k in v for k in ("left", "top", "width", "height")):
        l = float(v["left"])
        t = float(v["top"])
        r = l + float(v["width"])
        b = t + float(v["height"])
    else:
        l = t = 0.0
        r = l + MIN_SIZE
        b = t + MIN_SIZE
    return l, t, r, b


def walk_views(v: dict[str, Any]) -> list[dict[str, Any]]:
    out = [v]
    for c in v.get("children", []) or []:
        out.extend(walk_views(c))
    return out


def color():
    r = random.randint(80, 200)
    g = random.randint(80, 200)
    b = random.randint(80, 200)
    return f"rgba({r},{g},{b},0.28)"


def render_example(idx: int, ex: dict[str, Any], out_dir: Path):
    views = walk_views(ex)
    if not views:
        return
    root_rect = to_rect(views[0])
    width = max(root_rect[2] - root_rect[0], MIN_SIZE)
    height = max(root_rect[3] - root_rect[1], MIN_SIZE)

    svg_elems = []
    # draw background
    svg_elems.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="white" stroke="black" stroke-width="1"/>'
    )
    for v in views:
        l, t, r, b = to_rect(v)
        w = max(r - l, MIN_SIZE)
        h = max(b - t, MIN_SIZE)
        fill = color()
        name = v.get("name", "unknown")
        svg_elems.append(
            f'<g><rect x="{l}" y="{t}" width="{w}" height="{h}" '
            f'fill="{fill}" stroke="black" stroke-width="0.5"/>'
            f'<text x="{l + 2}" y="{t + 12}" font-size="10" '
            f'fill="black">{name}</text></g>'
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        + "\n".join(svg_elems)
        + "\n</svg>\n"
    )
    out_path = out_dir / f"example_{idx}.svg"
    out_path.write_text(svg)
    print(f"wrote {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Visualize mockdown examples to SVG.")
    parser.add_argument("json_file", type=Path, help="Input JSON file")
    parser.add_argument("--out", type=Path, default=Path("tmp/viz"), help="Output dir")
    args = parser.parse_args()

    examples = load_examples(args.json_file)
    args.out.mkdir(parents=True, exist_ok=True)
    for i, ex in enumerate(examples):
        render_example(i, ex, args.out)


if __name__ == "__main__":
    main()

