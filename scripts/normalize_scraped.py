#!/usr/bin/env python3
"""
Normalize scraped mockdown-style JSON:
- Ensure every view has a rect field.
- If rect is missing, derive from left/top/width/height or default to a 1x1 box.
- If rect has zero/negative size, expand to at least 1 pixel in each dimension.
- Preserve non-isomorphic structures (no name intersection).

Usage:
    uv run python3 scripts/normalize_scraped.py data/generated/foo.json ...
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

MIN_SIZE = 1.0
MAX_DIM = 8000.0


def fix_rect(v: dict[str, Any]) -> list[float]:
    if "rect" in v and isinstance(v["rect"], (list, tuple)) and len(v["rect"]) == 4:
        l, t, r, b = [float(x) for x in v["rect"]]
    elif all(k in v for k in ("left", "top", "width", "height")):
        l = float(v["left"])
        t = float(v["top"])
        w = float(v["width"])
        h = float(v["height"])
        r = l + w
        b = t + h
    else:
        l = t = 0.0
        r = l + MIN_SIZE
        b = t + MIN_SIZE

    # enforce minimum size
    w = r - l
    h = b - t
    if w < MIN_SIZE:
        r = l + MIN_SIZE
        w = MIN_SIZE
    if h < MIN_SIZE:
        b = t + MIN_SIZE
        h = MIN_SIZE

    # clamp excessively large boxes by scaling down about the top-left
    scale = min(1.0, MAX_DIM / max(w, h))
    if scale < 1.0:
        w *= scale
        h *= scale
        r = l + w
        b = t + h

    # hard clamp to MAX_DIM to avoid float drift over threshold
    w = min(w, MAX_DIM)
    h = min(h, MAX_DIM)
    r = l + w
    b = t + h

    return [l, t, r, b]


def normalize_view(v: dict[str, Any]) -> dict[str, Any]:
    v = dict(v)
    v["rect"] = fix_rect(v)
    children = v.get("children", [])
    if isinstance(children, list):
        v["children"] = [normalize_view(c) for c in children]
    else:
        v["children"] = []
    return v


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
        # fallback: single list value
        vals = list(data.values())
        if len(vals) == 1 and isinstance(vals[0], list):
            return vals[0]
    raise ValueError(f"Unsupported format in {path}")


def save_examples(path: Path, examples: list[dict[str, Any]]) -> None:
    out = {"examples": examples}
    with path.open("w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")


def process_file(path: Path) -> None:
    examples = load_examples(path)
    normalized = [normalize_view(ex) for ex in examples]
    save_examples(path, normalized)
    print(f"normalized {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path, help="JSON files to normalize")
    args = parser.parse_args()
    for p in args.files:
        process_file(p)


if __name__ == "__main__":
    main()

