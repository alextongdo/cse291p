#!/usr/bin/env python3
"""
Simplify a live page to a static HTML snapshot for scraping.

Usage:
  uv run python simplify_html.py https://www.cnn.com ../data/generated/cnn_simplified.html
"""

import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


NOISE_SELECTORS = [
    "script",
    "style",
    "noscript",
    "iframe",
    "video",
    "audio",
    "canvas",
    "object",
    "embed",
    "link[rel=preload]",
]

AD_HINT_SELECTORS = [
    "[id*='ad']",
    "[class*='ad-']",
    "[class*='advert']",
    "[class*='banner']",
    "[class*='cookie']",
]


async def simplify(
    url: str,
    out_path: Path,
    wait_until: str = "domcontentloaded",
    timeout_ms: int = 60000,
    keep_styles: bool = False,
):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until=wait_until, timeout=timeout_ms)

        remove_list = NOISE_SELECTORS.copy()
        if keep_styles:
            remove_list = [sel for sel in remove_list if sel not in ("style", "link[rel=preload]")]

        await page.evaluate(
            """
({ removeSelectors, adSelectors }) => {
  removeSelectors.forEach(sel => document.querySelectorAll(sel).forEach(el => el.remove()));
  adSelectors.forEach(sel => document.querySelectorAll(sel).forEach(el => el.remove()));
}
""",
            {"removeSelectors": remove_list, "adSelectors": AD_HINT_SELECTORS},
        )

        html = await page.content()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        await browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out_html", type=Path)
    ap.add_argument("--keep-styles", action="store_true", help="do not remove <style> or preload links")
    args = ap.parse_args()
    asyncio.run(simplify(args.url, args.out_html, keep_styles=args.keep_styles))


if __name__ == "__main__":
    main()

