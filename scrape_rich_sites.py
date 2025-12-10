"""
Scrape a small set of “rich” sites at one horizontal and one vertical viewport,
then emit deterministic jittered variants.

- Base scrape: 3 copies per orientation (desktop/tablet-ish and mobile-ish)
- Jitter set A: 3 copies with random 1–10 px perturbations
- Jitter set B: 3 copies with a different seed, same jitter bounds

Total per orientation: 9 examples. Two orientations → 18 examples per site.

This uses Playwright (Chromium). Make sure browsers are installed:
    playwright install chromium

Usage:
    python scrape_rich_sites.py

Outputs:
    data/generated/<slug>_scraped.json
"""

import asyncio
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from playwright.async_api import async_playwright

RICH_SITES = [
    ("wikipedia", "https://www.wikipedia.org"),
    ("developer_mozilla", "https://developer.mozilla.org/en-US/"),
    ("hacker_news", "https://news.ycombinator.com"),
    ("bbc", "https://www.bbc.com"),
    ("guardian", "https://www.theguardian.com/international"),
    ("cnn", "https://www.cnn.com"),
    ("theverge", "https://www.theverge.com"),
    ("nytimes", "https://www.nytimes.com"),
    ("mozilla", "https://www.mozilla.org"),
    ("npr", "https://www.npr.org"),
]

# One horizontal-ish, one vertical-ish
VIEWPORTS = {
    "horizontal": {"width": 1280, "height": 900},
    "vertical": {"width": 360, "height": 760},
}

OUT_DIR = Path("data/generated")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PAYLOAD = """
(selector) => {
  const root = document.querySelector(selector);
  if (!root) { return null; }

  const excludedSelectors = [
    'p > *','h1 > *','h2 > *','h3 > *','h4 > *','h5 > *','h6 > *','select > *'
  ];

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

  function isVisible(rect) {
    return rect.width > 0 && rect.height > 0;
  }

  function isExcluded(el) {
    return excludedSelectors.some((sel) => el.matches(sel));
  }

  function isDisjoint(r1, r2) {
    return r1.left > r2.right || r1.right < r2.left || r1.top > r2.bottom || r1.bottom < r2.top;
  }

  function scrape(el, parent) {
    const rect = el.getBoundingClientRect();
    if (isExcluded(el)) return null;
    if (!isVisible(rect)) return null;
    if (parent) {
      const pr = parent.getBoundingClientRect();
      if (isDisjoint(rect, pr)) return null;
    }

    const children = Array.from(el.children)
      .map((c) => scrape(c, el))
      .filter(Boolean);

    return {
      name: mangle(el),
      rect: [
        rect.left + window.scrollX,
        rect.top + window.scrollY,
        rect.right,
        rect.bottom,
      ],
      children,
    };
  }

  return scrape(root, null);
}
"""


def jitter_rect(rect: List[float], lo: int, hi: int, *, seed: int) -> List[float]:
    random.seed(seed)
    l, t, r, b = rect
    dl = random.randint(-hi, -lo) if random.random() < 0.5 else random.randint(lo, hi)
    dt = random.randint(-hi, -lo) if random.random() < 0.5 else random.randint(lo, hi)
    dr = random.randint(-hi, -lo) if random.random() < 0.5 else random.randint(lo, hi)
    db = random.randint(-hi, -lo) if random.random() < 0.5 else random.randint(lo, hi)
    nl = l + dl
    nt = t + dt
    nr = max(nl + 1, r + dr)
    nb = max(nt + 1, b + db)
    return [nl, nt, nr, nb]


def jitter_view(node: Dict[str, Any], lo: int, hi: int, *, seed: int) -> Dict[str, Any]:
    jnode = {
        "name": node["name"],
        "rect": jitter_rect(node["rect"], lo, hi, seed=seed),
        "children": [],
    }
    for i, child in enumerate(node.get("children", [])):
        jnode["children"].append(jitter_view(child, lo, hi, seed=seed + i + 1))
    return jnode


def replicate_with_jitter(base: Dict[str, Any]) -> List[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []
    # 3 copies of base
    for _ in range(3):
        samples.append(base)
    # jitter set A seeds 100..102
    for s in range(100, 103):
        samples.append(jitter_view(base, 1, 10, seed=s))
    # jitter set B seeds 200..202
    for s in range(200, 203):
        samples.append(jitter_view(base, 1, 10, seed=s))
    return samples


@dataclass
class ScrapeResult:
    orientation: str
    viewport: Dict[str, int]
    examples: List[Dict[str, Any]]


async def scrape_once(page, url: str, viewport: Dict[str, int]) -> Dict[str, Any]:
    await page.set_viewport_size(viewport)
    await page.goto(url, wait_until="load", timeout=60000)
    data = await page.evaluate(PAYLOAD, "body")
    if not data:
        raise RuntimeError(f"Failed to scrape {url} at {viewport}")
    return data


async def scrape_site(play, slug: str, url: str) -> List[ScrapeResult]:
    browser = await play.chromium.launch(headless=True)
    page = await browser.new_page()
    results: List[ScrapeResult] = []
    try:
        for orient, vp in VIEWPORTS.items():
            base = await scrape_once(page, url, vp)
            augmented = replicate_with_jitter(base)
            results.append(ScrapeResult(orientation=orient, viewport=vp, examples=augmented))
    finally:
        await browser.close()
    return results


async def main():
    async with async_playwright() as play:
        for slug, url in RICH_SITES:
            print(f"Scraping {slug}: {url}")
            try:
                results = await scrape_site(play, slug, url)
            except Exception as exc:
                print(f"  FAILED: {exc}")
                continue

            out_examples = []
            for res in results:
                # annotate viewport
                for ex in res.examples:
                    ex["_viewport"] = {
                        "width": res.viewport["width"],
                        "height": res.viewport["height"],
                        "label": res.orientation,
                        "category": "mobile" if res.orientation == "vertical" else "desktop",
                    }
                out_examples.extend(res.examples)

            out_path = OUT_DIR / f"{slug}_scraped.json"
            out_path.write_text(json.dumps({"examples": out_examples}, indent=2))
            print(f"  wrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())

