"""
Iterate over /original HTMLs, scrape 3 slightly-jittered horizontal and
3 slightly-jittered vertical examples, train on a subset, validate on
held-out examples, and keep sites with val RMSD <= 5. Writes combined
output to data/generated/selected_prepared.json. manual_cnn.json is
untouched.
"""

import asyncio
import json
import random
import re
from urllib.parse import urlparse
from pathlib import Path
from typing import Any, Dict, List, Tuple

from playwright.async_api import async_playwright

from src.main import ConditionalMockdown
from src.types import View
from src.evaluation import calculate_rmsd, calculate_accuracy

ROOT = Path("data/generated/selected_prepared.json")
ORIGINAL_DIR = Path("original")
H_VIEWPORT = {"width": 1280, "height": 900}
V_VIEWPORT = {"width": 360, "height": 760}
MIN_CHILDREN = 3
MAX_KEEP = 9
# train/val split indices for 3H + 3V examples in order [h0,h1,h2,v0,v1,v2]
TRAIN_IDXS = [0, 1, 3, 4]
VAL_IDXS = [2, 5]

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
    if (el.className) prefix += `.${String(el.className).replace(/\s+/g, '.')}`;
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
    return { name: mangle(el), rect: [rect.left + window.scrollX, rect.top + window.scrollY, rect.right, rect.bottom], children };
  }
  return scrape(root);
}
"""


def clamp_children(node: Dict[str, Any]) -> Dict[str, Any]:
    l, t, r, b = node["rect"]
    clamped = []
    for c in node.get("children", []):
        cl, ct, cr, cb = c["rect"]
        cl = max(l, min(cr, cl))
        ct = max(t, min(cb, ct))
        cr = min(r, max(cl + 1, cr))
        cb = min(b, max(ct + 1, cb))
        cc = dict(c)
        cc["rect"] = [cl, ct, cr, cb]
        cc = clamp_children(cc)
        clamped.append(cc)
    out = dict(node)
    out["children"] = clamped
    return out


def prune_depth(node: Dict[str, Any], depth: int = 1, max_depth: int = 5) -> Dict[str, Any]:
    node = dict(node)
    if depth >= max_depth:
        node["children"] = []
    else:
        node["children"] = [prune_depth(c, depth + 1, max_depth) for c in node.get("children", [])]
    return node


def sample_dxdy(seed: int) -> Tuple[int, int]:
    """Tiny width-only jitter; keep very close to original."""
    random.seed(seed)
    dx_choices = [-1, 0, 1]
    dx = random.choice(dx_choices)
    dy = 0
    return dx, dy


def translate_tree(node: Dict[str, Any], dx: int, dy: int) -> Dict[str, Any]:
    l, t, r, b = node["rect"]
    rect = [l + dx, t + dy, r + dx, b + dy]
    kids = [translate_tree(c, dx, dy) for c in node.get("children", [])]
    out = {"name": node["name"], "rect": rect, "children": kids}
    if "_viewport" in node:
        out["_viewport"] = node["_viewport"]
    return out


def jitter_example(node: Dict[str, Any], seed: int) -> Dict[str, Any]:
    dx, dy = sample_dxdy(seed)
    return translate_tree(node, dx, dy)


def to_view(node: Dict[str, Any]) -> View:
    vp = node.get("_viewport", {})
    children = [to_view(c) for c in node.get("children", [])]
    v = View(name=node["name"], rect=tuple(node["rect"]), children=children)
    setattr(v, "_viewport", vp)
    return v


async def render(play, html_path: Path, viewport: Dict[str, int]) -> Dict[str, Any]:
    page = await play.new_page(viewport=viewport)
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


def evaluate_train_val(examples: List[Dict[str, Any]]) -> Tuple[float, float]:
    train_views = [to_view(examples[i]) for i in TRAIN_IDXS]
    val_views = [to_view(examples[i]) for i in VAL_IDXS]
    cm = ConditionalMockdown()
    cm.fit(train_views)
    rmsds = []
    accs = []
    for gt in val_views:
        vp = getattr(gt, "_viewport", {})
        w = vp.get("width", gt.width)
        h = vp.get("height", gt.height)
        pred = cm.predict(width=w, height=h)
        rmsds.append(calculate_rmsd(pred, gt))
        accs.append(calculate_accuracy(pred, gt))
    return float(sum(rmsds) / len(rmsds)), float(sum(accs) / len(accs))


def extract_url(html_path: Path) -> str:
    head = html_path.read_text(errors="ignore").splitlines()[:10]
    for line in head:
        m = re.search(r"url:\s*(\S+)", line)
        if m:
            return m.group(1)
    return html_path.stem


def site_name(html_path: Path, url: str) -> str:
    if url:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if host.startswith("www."):
            host = host[4:]
        if host:
            # take hostname without TLD if present, else full host
            parts = host.split(".")
            if len(parts) > 1:
                return parts[0]
            return host
    return html_path.stem


def flatten_names(node: Dict[str, Any]) -> List[str]:
    names = [node.get("name", "")]
    for c in node.get("children", []):
        names.extend(flatten_names(c))
    return names


def count_children(node: Dict[str, Any]) -> int:
    cnt = len(node.get("children", []))
    for c in node.get("children", []):
        cnt += count_children(c)
    return cnt


def filter_tree_by_names(node: Dict[str, Any], allowed: set[str]) -> Dict[str, Any] | None:
    if node.get("name", "") not in allowed:
        return None
    kept_children = []
    for c in node.get("children", []):
        fc = filter_tree_by_names(c, allowed)
        if fc:
            kept_children.append(fc)
    out = dict(node)
    out["children"] = kept_children
    return out


async def main():
    html_files = sorted([p for p in ORIGINAL_DIR.glob("*.html") if p.is_file()])
    kept = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for html_path in html_files:
            if len(kept) >= MAX_KEEP:
                break
            url = extract_url(html_path)
            try:
                base_h = await render(browser, html_path, H_VIEWPORT)
                base_v = await render(browser, html_path, V_VIEWPORT)
            except Exception as e:
                print(f"skip {html_path.name}: scrape error {e}")
                continue

            examples: List[Dict[str, Any]] = []
            # 3 identical horizontals and 3 identical verticals (no jitter)
            for _ in range(3):
                examples.append(json.loads(json.dumps(base_h)))
            for _ in range(3):
                examples.append(json.loads(json.dumps(base_v)))

            examples = [clamp_children(prune_depth(ex, max_depth=4)) for ex in examples]

            if any(count_children(ex) < MIN_CHILDREN for ex in examples):
                print(f"{html_path.name} discarded: too few children")
                continue

            try:
                val_rmsd, val_acc = evaluate_train_val(examples)
            except Exception as e:
                print(f"{html_path.name} failed fit: {e}")
                continue
            if val_rmsd > 10:
                print(f"{html_path.name} discarded val_rmsd={val_rmsd:.3f}")
                continue
            site = site_name(html_path, url)
            kept.append(
                {
                    "site": site,
                    "url": url,
                    "examples": examples,
                    "val_rmsd": val_rmsd,
                    "val_accuracy": val_acc,
                    "train_indices": TRAIN_IDXS,
                    "val_indices": VAL_IDXS,
                }
            )
            print(f"kept {site} val_rmsd={val_rmsd:.3f} val_acc={val_acc:.3f} (total {len(kept)})")
        await browser.close()
    ROOT.write_text(json.dumps({"sites": kept}, indent=2))
    print(f"Saved {ROOT} with {len(kept)} sites")


asyncio.run(main())






