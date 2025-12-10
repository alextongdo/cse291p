"""
Render 9 local HTML files from ./original into rect trees with base copies only
(no jitter), then write per-source JSON into data/generated.

Per source:
- horizontal (1280x900): 3 base copies (unchanged) + 3 copies of one jittered tree
- vertical (360x760):    3 base copies (unchanged) + 3 copies of one jittered tree

Jitter: width-biased, uniform 5..10px (sign random) on x, and 3..6px on y,
applied as a single translation to the whole tree (preserves containment).
"""

import asyncio
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple

from playwright.async_api import async_playwright

ORIGINAL_DIR = Path("original")
OUT_DIR = Path("data/generated")
OUT_DIR.mkdir(parents=True, exist_ok=True)

H_VIEWPORT = {"width": 1280, "height": 900}
V_VIEWPORT = {"width": 360, "height": 760}

PAYLOAD = """
(selector) => {
  const root = document.querySelector(selector);
  if (!root) return null;
  const excludedSelectors = ['p > *','h1 > *','h2 > *','h3 > *','h4 > *','h5 > *','h6 > *','select > *'];
  const seenElements = new WeakMap();
  const seenPrefixes = {};
  function mangle(el) {
    if (seenElements.has(el)) return seenElements.get(el);
    let prefix = el.tagName.toLowerCase();
    if (el.id) prefix += `#${el.id}`;
    if (el.className) prefix += `.${String(el.className).replace(/\\s+/g, '.')}`;
    let times = seenPrefixes[prefix] || 0;
    seenPrefixes[prefix] = ++times;
    const name = `[${prefix}@${times}]`;
    seenElements.set(el, name);
    return name;
  }
  function isVisible(rect) { return rect.width > 0 && rect.height > 0; }
  function isExcluded(el) { return excludedSelectors.some(sel => el.matches(sel)); }
  function scrape(el) {
    const rect = el.getBoundingClientRect();
    if (isExcluded(el) || !isVisible(rect)) return null;
    const children = Array.from(el.children).map(scrape).filter(Boolean);
    return {
      name: mangle(el),
      rect: [rect.left + window.scrollX, rect.top + window.scrollY, rect.right, rect.bottom],
      children
    };
  }
  return scrape(root);
}
"""


def sample_dxdy(seed: int, x_lo=5, x_hi=10, y_lo=0, y_hi=0) -> Tuple[int, int]:
    random.seed(seed)
    dx = random.randint(x_lo, x_hi) * (1 if random.random() < 0.5 else -1)
    dy = random.randint(y_lo, y_hi) * (1 if random.random() < 0.5 else -1) if (y_hi - y_lo) > 0 else 0
    return dx, dy


def translate_tree(node: Dict[str, Any], dx: int, dy: int) -> Dict[str, Any]:
    l, t, r, b = node["rect"]
    rect = [l + dx, t + dy, r + dx, b + dy]
    kids = [translate_tree(c, dx, dy) for c in node.get("children", [])]
    jnode = {"name": node["name"], "rect": rect, "children": kids}
    if "_viewport" in node:
        jnode["_viewport"] = node["_viewport"]
    return jnode


def jitter_example(node: Dict[str, Any], seed: int, x_lo=5, x_hi=10, y_lo=0, y_hi=0) -> Dict[str, Any]:
    # Jitter only top two levels: shift root by dx0/dy0; then shift each
    # first-level child (and its subtree) by its own dx/dy. Deeper nodes keep
    # their relative geometry under their jittered parent.
    dx0, dy0 = sample_dxdy(seed, x_lo=x_lo, x_hi=x_hi, y_lo=y_lo, y_hi=y_hi)
    root = translate_tree(node, dx0, dy0)
    new_children = []
    for i, c in enumerate(root.get("children", [])):
        dx, dy = sample_dxdy(seed + i + 1, x_lo=x_lo, x_hi=x_hi, y_lo=y_lo, y_hi=y_hi)
        new_children.append(translate_tree(c, dx, dy))
    root["children"] = new_children
    return root


def prune_depth(node: Dict[str, Any], depth: int = 1, max_depth: int = 5) -> Dict[str, Any]:
    node = dict(node)
    if depth >= max_depth:
        node["children"] = []
    else:
        node["children"] = [prune_depth(c, depth + 1, max_depth) for c in node.get("children", [])]
    return node


def shrink_to_children(node: Dict[str, Any]) -> Dict[str, Any]:
    """Reset a node rect to the union of its children (if any), bottom-up."""
    kids = node.get("children", [])
    if not kids:
        return node
    shrunk_kids = [shrink_to_children(c) for c in kids]
    l = min(c["rect"][0] for c in shrunk_kids)
    t = min(c["rect"][1] for c in shrunk_kids)
    r = max(c["rect"][2] for c in shrunk_kids)
    b = max(c["rect"][3] for c in shrunk_kids)
    out = dict(node)
    out["children"] = shrunk_kids
    out["rect"] = [l, t, r, b]
    return out


def clamp_children(node: Dict[str, Any]) -> Dict[str, Any]:
    """Clamp each child's rect to lie within parent rect, recursively."""
    l, t, r, b = node["rect"]
    clamped_kids = []
    for c in node.get("children", []):
        cl, ct, cr, cb = c["rect"]
        cl = max(l, min(cr, cl))
        ct = max(t, min(cb, ct))
        cr = min(r, max(cl + 1, cr))
        cb = min(b, max(ct + 1, cb))
        cc = dict(c)
        cc["rect"] = [cl, ct, cr, cb]
        cc = clamp_children(cc)
        clamped_kids.append(cc)
    out = dict(node)
    out["children"] = clamped_kids
    return out


async def render_file(play, html_path: Path, viewport: Dict[str, int]) -> Dict[str, Any]:
    browser = await play.chromium.launch(headless=True)
    page = await browser.new_page(viewport=viewport)
    try:
        await page.goto(html_path.resolve().as_uri(), wait_until="load")
        data = await page.evaluate(PAYLOAD, "body")
        if not data:
            raise RuntimeError(f"Failed to scrape {html_path}")
        data["_viewport"] = {
            "width": viewport["width"],
            "height": viewport["height"],
            "label": "horizontal" if viewport["width"] >= viewport["height"] else "vertical",
            "category": "desktop" if viewport["width"] >= 700 else "mobile",
        }
        return data
    finally:
        await browser.close()


async def process_file(play, html_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    base_h = await render_file(play, html_path, H_VIEWPORT)
    base_v = await render_file(play, html_path, V_VIEWPORT)
    # base copies (no jitter)
    examples: List[Dict[str, Any]] = []
    for _ in range(3):
        examples.append(json.loads(json.dumps(base_h)))  # deep copy

    for _ in range(3):
        examples.append(json.loads(json.dumps(base_v)))

    # prune to depth<=5 for manageability
    pruned = [prune_depth(ex, max_depth=5) for ex in examples]
    # For bloomberg, shrink root to children union to keep content-cropped height
    # and clamp children to parent bounds to avoid leakage.
    if html_path.stem == "14":
        pruned = [clamp_children(shrink_to_children(ex)) for ex in pruned]
    return html_path.stem, pruned


async def main():
    html_files = sorted([p for p in ORIGINAL_DIR.glob("*.html") if p.is_file()])
    if len(html_files) < 9:
        raise SystemExit("Need at least 9 html files in ./original")
    selected = html_files[:9]
    async with async_playwright() as play:
        for html_path in selected:
            slug, examples = await process_file(play, html_path)
            out_path = OUT_DIR / f"{slug}_prepared.json"
            out_path.write_text(json.dumps({"examples": examples}, indent=2))
            print(f"Wrote {out_path} ({len(examples)} examples)")


if __name__ == "__main__":
    asyncio.run(main())



