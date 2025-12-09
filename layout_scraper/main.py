#!/usr/bin/env python3
"""
Layout Scraper: Capture geometric layout of HTML elements across viewports.

Captures "conditional layouts" where elements change position/size based on
viewport width. Useful for building datasets for layout synthesis tools.

Usage:
    python main.py [--config CONFIG_FILE] [--output-dir OUTPUT_DIR]
    
Example:
    python main.py --config config.json --output-dir ../data/generated
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# Default viewports if not specified in config
DEFAULT_VIEWPORTS = {
    "wide": [
        {"width": 1920, "height": 1080, "label": "desktop_large"},
        {"width": 1366, "height": 768, "label": "desktop_medium"},
        {"width": 1024, "height": 768, "label": "tablet_landscape"},
    ],
    "thin": [
        {"width": 375, "height": 812, "label": "iphone_x"},
        {"width": 414, "height": 896, "label": "iphone_xr"},
        {"width": 360, "height": 800, "label": "android_small"},
    ],
}


async def extract_element_bounds(
    page: Page,
    selector: str,
    timeout_ms: int = 5000
) -> dict[str, Any] | None:
    """
    Extract bounding box for a single element.
    
    Returns:
        Dict with x, y, width, height or None if element not found/visible.
    """
    try:
        locator = page.locator(selector).first
        
        # Check if element exists and is visible
        if not await locator.is_visible(timeout=timeout_ms):
            return None
        
        bbox = await locator.bounding_box()
        if bbox is None:
            return None
        
        return {
            "x": round(bbox["x"], 2),
            "y": round(bbox["y"], 2),
            "width": round(bbox["width"], 2),
            "height": round(bbox["height"], 2),
            # Also compute right/bottom for convenience
            "right": round(bbox["x"] + bbox["width"], 2),
            "bottom": round(bbox["y"] + bbox["height"], 2),
        }
    except PlaywrightTimeout:
        return None
    except Exception as e:
        logger.debug(f"Error extracting bounds for '{selector}': {e}")
        return None


async def extract_all_matching_elements(
    page: Page,
    selector: str,
    timeout_ms: int = 5000
) -> list[dict[str, Any]]:
    """
    Extract bounding boxes for ALL elements matching a selector.
    
    Useful for repeated elements like list items, cards, etc.
    Returns list of bounds dicts, empty list if none found.
    """
    results = []
    try:
        locator = page.locator(selector)
        count = await locator.count()
        
        for i in range(min(count, 50)):  # Cap at 50 to avoid huge datasets
            try:
                elem = locator.nth(i)
                if await elem.is_visible(timeout=timeout_ms):
                    bbox = await elem.bounding_box()
                    if bbox:
                        results.append({
                            "index": i,
                            "x": round(bbox["x"], 2),
                            "y": round(bbox["y"], 2),
                            "width": round(bbox["width"], 2),
                            "height": round(bbox["height"], 2),
                            "right": round(bbox["x"] + bbox["width"], 2),
                            "bottom": round(bbox["y"] + bbox["height"], 2),
                        })
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"Error extracting all elements for '{selector}': {e}")
    
    return results


async def capture_viewport(
    page: Page,
    selectors: list[str],
    viewport: dict,
    wait_ms: int = 1000,
    timeout_ms: int = 5000
) -> dict[str, Any]:
    """
    Capture layout data for a single viewport.
    
    Args:
        page: Playwright page object
        selectors: List of CSS selectors to track
        viewport: Dict with width, height, label
        wait_ms: Milliseconds to wait after resize
        timeout_ms: Timeout for element detection
    
    Returns:
        Dict with viewport info and element bounds
    """
    width = viewport["width"]
    height = viewport["height"]
    label = viewport.get("label", f"{width}x{height}")
    
    logger.info(f"  Capturing viewport: {label} ({width}x{height})")
    
    # Resize viewport
    await page.set_viewport_size({"width": width, "height": height})
    
    # Wait for CSS transitions/reflow to settle
    await asyncio.sleep(wait_ms / 1000)
    
    # Extract bounds for each selector
    elements = {}
    for selector in selectors:
        # Get first matching element
        bounds = await extract_element_bounds(page, selector, timeout_ms)
        
        # Also get all matching elements if there are multiple
        all_bounds = await extract_all_matching_elements(page, selector, timeout_ms)
        
        elements[selector] = {
            "first": bounds,
            "all": all_bounds if len(all_bounds) > 1 else None,
            "count": len(all_bounds),
        }
    
    return {
        "viewport": {
            "width": width,
            "height": height,
            "label": label,
            "category": "wide" if width >= 768 else "thin",
        },
        "elements": elements,
    }


async def capture_site(
    page: Page,
    site_config: dict,
    viewports: dict,
    settings: dict,
) -> dict[str, Any]:
    """
    Capture layout data for a single site across all viewports.
    
    Args:
        page: Playwright page object
        site_config: Dict with url, name, selectors
        viewports: Dict with wide and thin viewport lists
        settings: Dict with wait_after_resize_ms, timeout_ms
    
    Returns:
        Complete layout data for the site
    """
    url = site_config["url"]
    name = site_config["name"]
    selectors = site_config["selectors"]
    
    wait_ms = settings.get("wait_after_resize_ms", 1000)
    timeout_ms = settings.get("timeout_ms", 30000)
    wait_until = settings.get("wait_until", "domcontentloaded")
    
    logger.info(f"Capturing site: {name} ({url})")
    
    # Navigate to the URL
    await page.goto(url, wait_until=wait_until, timeout=timeout_ms)

    # Simplify page: remove obvious noise (scripts, styles, iframes, ads, svg icons)
    # Inspired by DCGen's simplify step; conservative to avoid breaking layout.
    await page.evaluate(
        """
(() => {
  const removeSelectors = [
    'script', 'style', 'noscript', 'iframe', 'link[rel=preload]',
    'video', 'audio', 'canvas', 'svg', 'object', 'embed'
  ];
  removeSelectors.forEach(sel => {
    document.querySelectorAll(sel).forEach(el => el.remove());
  });
  // Remove obvious ads/trackers by attribute hints
  document.querySelectorAll('[id*="ad"], [class*="ad-"], [class*="advert"], [class*="banner"], [class*="cookie"]').forEach(el => el.remove());
})();
"""
    )
    
    # Capture all viewports
    viewport_data = []
    
    # Wide viewports first
    for vp in viewports.get("wide", []):
        data = await capture_viewport(page, selectors, vp, wait_ms, timeout_ms)
        viewport_data.append(data)
    
    # Then thin viewports
    for vp in viewports.get("thin", []):
        data = await capture_viewport(page, selectors, vp, wait_ms, timeout_ms)
        viewport_data.append(data)
    
    return {
        "site": {
            "url": url,
            "name": name,
            "captured_at": datetime.now().isoformat(),
        },
        "selectors": selectors,
        "viewports": viewport_data,
    }


def convert_to_mockdown_format(site_data: dict) -> dict:
    """
    Convert captured data to a Mockdown-compatible format.

    The original Mockdown datasets use per-node fields:
      { "name": ..., "top": ..., "left": ..., "height": ..., "width": ..., "children": [...] }
    We mirror that here (flat hierarchy with the tracked selectors).
    """
    examples = []

    for vp_data in site_data["viewports"]:
        viewport = vp_data["viewport"]
        elements = vp_data["elements"]

        children = []
        for selector, bounds_data in elements.items():
            bounds = bounds_data["first"]
            if bounds is None:
                continue

            # Clean selector name for use as view name
            view_name = (
                selector.replace("#", "")
                .replace(".", "")
                .replace(" ", "_")
                .replace(">", "_")
                .replace("[", "_")
                .replace("]", "")
            )

            children.append(
                {
                    "name": view_name,
                    "rect": [
                        bounds["x"],
                        bounds["y"],
                        bounds["x"] + bounds["width"],
                        bounds["y"] + bounds["height"],
                    ],
                    "top": bounds["y"],
                    "left": bounds["x"],
                    "height": bounds["height"],
                    "width": bounds["width"],
                    "children": [],
                }
            )

        if children:
            examples.append(
                {
                    "name": "root",
                    "rect": [0, 0, viewport["width"], viewport["height"]],
                    "top": 0,
                    "left": 0,
                    "height": viewport["height"],
                    "width": viewport["width"],
                    "children": children,
                    "_viewport": viewport,  # Metadata
                }
            )

    return {"examples": examples}


async def main_async(config_path: str, output_dir: str):
    """Main async entry point."""
    
    # Load configuration
    config_file = Path(config_path)
    if not config_file.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_file) as f:
        config = json.load(f)
    
    sites = config.get("sites", [])
    viewports = config.get("viewports", DEFAULT_VIEWPORTS)
    settings = config.get("settings", {})
    default_selectors = config.get("default_selectors", [])
    
    if not sites:
        logger.error("No sites configured")
        sys.exit(1)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting layout capture for {len(sites)} site(s)")
    logger.info(f"Output directory: {output_path.absolute()}")
    
    results = []
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        for site_config in sites:
            try:
                selectors = site_config.get("selectors") or default_selectors
                site_conf = dict(site_config)
                site_conf["selectors"] = selectors

                site_data = await capture_site(page, site_conf, viewports, settings)
                results.append(site_data)
                
                # Save individual site data
                site_name = site_config["name"]
                
                # Raw format (grouped by viewport)
                raw_output = output_path / f"{site_name}_raw.json"
                with open(raw_output, "w") as f:
                    json.dump(site_data, f, indent=2)
                logger.info(f"  Saved raw data: {raw_output}")
                
                # Mockdown format
                mockdown_data = convert_to_mockdown_format(site_data)
                mockdown_output = output_path / f"{site_name}_mockdown.json"
                with open(mockdown_output, "w") as f:
                    json.dump(mockdown_data, f, indent=2)
                logger.info(f"  Saved Mockdown format: {mockdown_output}")
                
            except Exception as e:
                logger.error(f"Failed to capture {site_config.get('name', 'unknown')}: {e}")
                continue
        
        await browser.close()
    
    # Save combined results
    if results:
        combined_output = output_path / "all_sites.json"
        with open(combined_output, "w") as f:
            json.dump({"sites": results}, f, indent=2)
        logger.info(f"Saved combined data: {combined_output}")
    
    logger.info(f"Capture complete! {len(results)}/{len(sites)} sites succeeded")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Capture HTML element layouts across viewports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py
    python main.py --config my_config.json
    python main.py --output-dir ./output
        """
    )
    parser.add_argument(
        "--config", "-c",
        default="config.json",
        help="Path to configuration JSON file (default: config.json)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="../data/generated",
        help="Output directory for captured data (default: ../data/generated)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(main_async(args.config, args.output_dir))


if __name__ == "__main__":
    main()

