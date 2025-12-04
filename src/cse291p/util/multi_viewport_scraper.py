"""Multi-viewport web scraper for capturing responsive layouts.

This utility scrapes the same website at multiple viewport sizes to capture
different structural layouts (e.g., 3 columns -> 1 column when width changes).

Reimplements and extends:
- mockdown/src/mockdown/scraping/scraper.py

Usage as script:
    python -m cse291p.util.multi_viewport_scraper <url> [output_file]

    Example:
        python -m cse291p.util.multi_viewport_scraper https://example.com output.json
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

log = logging.getLogger(__name__)

# Exclusions taken from Tree.js in auto-mock.
DEFAULT_EXCLUDED_SELECTORS = [
    "p > *",
    "h1 > *",
    "h2 > *",
    "h3 > *",
    "h4 > *",
    "h5 > *",
    "h6 > *",
    "select > *",
]

# JavaScript payload for scraping DOM structure
# language=JavaScript
PAYLOAD = """
    const rootElement = arguments[0];
    const excludedSelectors = arguments[1];
    
    // This has to be a WeakMap, as in a normal object, DOM node keys will be
    // coerced to strings, which are not unique and will cause collisions.
    var seenElements = new WeakMap();
    var seenPrefixes = {};
    
    function mangle(el) {
        if (seenElements.has(el)) {
            return seenElements.get(el);
        }
    
        let prefix = `${el.tagName.toLowerCase()}`;
        
        if (el.id) {
            prefix += `#${el.id}`;
        }
        if (el.className) { 
            prefix += `.${String(el.className).replace(/\\s+/g, '.')}`; 
        }
        
        // Ensure duplicate prefixes get unique numeric suffixes.
        let timesSeen = seenPrefixes[prefix] || 0;
        seenPrefixes[prefix] = ++timesSeen;
        
        // Store the mangled name for this element and return it.
        const name = `[${prefix}@${timesSeen}]`;
        seenElements.set(el, name);
        return name;
    }
    
    function isVisible(rect) {
        return rect.width > 0 && rect.height > 0; 
    }
    
    function isExcluded(el) {
        return excludedSelectors.some((sel) => el.matches(sel));
    }
    
    function isContained(child, parent) {
        /* Is rect1 contained in rect2? */
        return child.left   >= parent.left 
            && child.top    >= parent.top
            && child.right  <= parent.right
            && child.bottom <= parent.bottom;
    }
    
    function isDisjoint(rect1, rect2) {
        return rect1.left   > rect2.right  // R1 is completely right of R2.
            || rect1.right  < rect2.left   // R1 is completely left of R2.
            || rect1.top    > rect2.bottom // R1 is completely below R2.
            || rect1.bottom < rect2.top    // R1 is completely above R2.
    }
    
    function scrape(el, parent) {
        const children = Array.from(el.children);
        const rect = el.getBoundingClientRect();
        
        if (isExcluded(el)) return [];
        if (!isVisible(rect)) return [];
        if (parent) {
            const parentRect = parent.getBoundingClientRect();
            if (isDisjoint(rect, parentRect)) {
                console.warn(`${mangle(el)} is disjoint from ${mangle(parent)}!`)
                return [];  // todo: too strict?
            }
        }

        // A bunch of duplication, but it's convenient for debugging.
        const data = {
            name: mangle(el),
            children: children.flatMap(c => scrape(c, el)),
            rect: [
                rect.left + window.scrollX,
                rect.top + window.scrollY,
                rect.right,
                rect.bottom
            ]           
        };
        return data;
    }
    
    return scrape(rootElement, undefined);
"""

SANITIZED_KEY_ORDER = ("name", "rect", "children")


class MultiViewportScraper:
    """
    Scraper that captures multiple viewport sizes to detect responsive layout changes.

    This is useful for capturing structurally different layouts
    (e.g., 3 columns -> 1 column) that occur when viewport dimensions change.
    """

    def __init__(self, headless: bool = True):
        """Initialize the scraper.

        Args:
            headless: Whether to run Chrome in headless mode (default: True)
        """
        opts = webdriver.ChromeOptions()
        if headless:
            opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)

        # Set a realistic user agent to avoid bot detection
        opts.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Set logging preferences
        opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})

        try:
            self.driver = webdriver.Chrome(options=opts)
            # Execute script to hide webdriver property
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
                },
            )
            self.driver.set_window_size(1920, 1080)
        except WebDriverException as wde:
            log.error(
                "You need to install chromedriver. "
                "Install via: brew install chromedriver (macOS) or "
                "download from https://chromedriver.chromium.org/"
            )
            raise wde

    def scrape_single_viewport(
        self,
        url: str,
        dims: tuple[int, int],
        root_selector: str = "body",
        wait_time: float = 1.0,
    ) -> dict[str, Any]:
        """Scrape a single viewport size.

        Args:
            url: URL to scrape
            dims: (width, height) tuple for viewport size
            root_selector: CSS selector for root element (default: "body")
            wait_time: Time to wait after page load in seconds (default: 1.0)

        Returns:
            Dictionary with 'example' (layout data) and 'screenshot' (base64 image)
        """
        import time

        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.support.ui import WebDriverWait

        width, height = dims

        try:
            self.driver.set_window_size(width, height)
            self.driver.get(url)

            # Wait for page to be interactive
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return document.readyState")
                    == "complete"
                )
            except TimeoutException:
                log.warning(
                    f"Page load timeout for {url} at {dims}, continuing anyway..."
                )

            # Wait for JavaScript to potentially render content
            time.sleep(wait_time)

            # Additional wait for dynamic content - wait for body to have children
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda d: len(
                        d.find_elements(By.CSS_SELECTOR, f"{root_selector} > *")
                    )
                    > 0
                )
            except TimeoutException:
                log.warning(
                    f"No children found in {root_selector}, continuing anyway..."
                )

            # Extra wait for JavaScript-heavy pages
            time.sleep(max(2.0, wait_time * 0.5))

            # Scroll to trigger lazy loading
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(0.5)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)

            # Find root element
            el = self.driver.find_element(By.CSS_SELECTOR, root_selector)

            # Execute scraping script
            data = self.driver.execute_script(PAYLOAD, el, DEFAULT_EXCLUDED_SELECTORS)
            screenshot = (
                "data:image/png;base64," + self.driver.get_screenshot_as_base64()
            )

            # Clean output
            cleaned_data = self._clean_output(data)

            return {
                "example": cleaned_data,
                "screenshot": screenshot,
                "viewport": {"width": width, "height": height},
            }
        except Exception as e:
            log.error(f"Error scraping {url} at {dims}: {e}")
            raise

    def scrape_multiple_viewports(
        self,
        url: str,
        viewports: list[tuple[int, int]],
        root_selector: str = "body",
        wait_time: float = 1.0,
    ) -> dict[str, Any]:
        """Scrape the same website at multiple viewport sizes.

        This captures different structural layouts that occur at different screen sizes,
        which is useful for conditional constraint synthesis.

        Args:
            url: URL to scrape
            viewports: List of (width, height) tuples for different viewport sizes
            root_selector: CSS selector for root element (default: "body")
            wait_time: Time to wait after each page load in seconds (default: 1.0)

        Returns:
            Dictionary with 'meta', 'examples', and 'captures' keys, compatible with
            Mockdown input format. Each example corresponds to one viewport size.
        """
        examples = []
        captures = []

        log.info(f"Scraping {url} at {len(viewports)} viewport sizes...")

        for i, (width, height) in enumerate(viewports, 1):
            log.info(f"  [{i}/{len(viewports)}] Scraping at {width}x{height}...")
            result = self.scrape_single_viewport(
                url, (width, height), root_selector, wait_time
            )
            examples.append(result["example"])
            captures.append(result["screenshot"])

        return {
            "meta": {
                "scrape": {
                    "origin": url,
                    "viewports": [{"width": w, "height": h} for w, h in viewports],
                }
            },
            "examples": examples,
            "captures": captures,
        }

    def scrape_responsive_breakpoints(
        self,
        url: str,
        root_selector: str = "body",
        wait_time: float = 1.0,
        custom_viewports: list[tuple[int, int]] | None = None,
    ) -> dict[str, Any]:
        """Scrape at common responsive breakpoints.

        Uses a predefined set of viewport sizes that commonly trigger layout changes:
        - Mobile portrait (320x568)
        - Mobile landscape (568x320)
        - Tablet portrait (768x1024)
        - Tablet landscape (1024x768)
        - Desktop small (1280x800)
        - Desktop large (1920x1080)
        - Ultra-wide (2560x1440)

        Args:
            url: URL to scrape
            root_selector: CSS selector for root element (default: "body")
            wait_time: Time to wait after each page load in seconds (default: 1.0)
            custom_viewports: Optional custom list of (width, height) tuples to use
            instead

        Returns:
            Dictionary with 'meta', 'examples', and 'captures' keys
        """
        if custom_viewports is None:
            # Common responsive breakpoints
            viewports = [
                (320, 568),  # Mobile portrait (iPhone SE)
                (568, 320),  # Mobile landscape
                (768, 1024),  # Tablet portrait (iPad)
                (1024, 768),  # Tablet landscape
                (1280, 800),  # Desktop small
                (1920, 1080),  # Desktop large
                (2560, 1440),  # Ultra-wide
            ]
        else:
            viewports = custom_viewports

        return self.scrape_multiple_viewports(url, viewports, root_selector, wait_time)

    def scrape_structured_viewports(
        self, url: str, root_selector: str = "body", wait_time: float = 1.0
    ) -> dict[str, Any]:
        """Scrape with structured viewport sizes: 3 regular, 3 flat/wide,
        3 skinny/tall, 1 standard.

        This generates 10 viewport sizes designed to capture different aspect ratios:
        - 3 regular sizes: Standard aspect ratios (16:9, 4:3, 3:2) with slight
                           variations
        - 3 flat/wide sizes: Wide aspect ratios (21:9, 16:10, 2:1) with variations
        - 3 skinny/tall sizes: Tall aspect ratios (9:16, 3:4, 2:3) with variations
        - 1 standard desktop: Common desktop size (1920x1080)

        Args:
            url: URL to scrape
            root_selector: CSS selector for root element (default: "body")
            wait_time: Time to wait after each page load in seconds (default: 1.0)

        Returns:
            Dictionary with 'meta', 'examples', and 'captures' keys
        """
        viewports = self._generate_structured_viewports()
        return self.scrape_multiple_viewports(url, viewports, root_selector, wait_time)

    def _generate_structured_viewports(self) -> list[tuple[int, int]]:
        """Generate 10 structured viewport sizes.

        Returns:
            List of (width, height) tuples: 3 regular, 3 flat, 3 skinny, 1 standard
        """
        viewports = []

        # 3 Regular sizes with slight variations in aspect ratio
        # Base: ~16:9, ~4:3, ~3:2 with slight variations
        viewports.extend(
            [
                (1920, 1080),  # Standard 16:9
                (1600, 1200),  # 4:3 aspect ratio
                (1800, 1200),  # 3:2 aspect ratio
            ]
        )

        # 3 Flat/wide sizes with variations in aspect ratio
        # Wide aspect ratios: 21:9, 16:10, 2:1
        viewports.extend(
            [
                (2560, 1080),  # 21:9 ultra-wide
                (1920, 1200),  # 16:10 wide
                (2400, 1200),  # 2:1 very wide
            ]
        )

        # 3 Skinny/tall sizes with variations in aspect ratio
        # Tall aspect ratios: 9:16, 3:4, 2:3
        viewports.extend(
            [
                (1080, 1920),  # 9:16 portrait (phone)
                (900, 1200),  # 3:4 portrait
                (800, 1200),  # 2:3 portrait
            ]
        )

        # 1 Standard desktop size (different from regular to ensure 10 total)
        viewports.append((1280, 720))  # Standard desktop 16:9 (smaller variant)

        return viewports

    def _clean_output(
        self, data: dict[str, Any], order: tuple[str, ...] = SANITIZED_KEY_ORDER
    ) -> dict[str, Any]:
        """Recursively reorder keys in output JSON.

        Puts 'children' last for better readability during inspection.
        """
        return {
            k: (
                [self._clean_output(c, order) for c in data[k]]
                if k == "children"
                else data[k]
            )
            for k in order
        }

    def cleanup(self):
        """Close the browser driver."""
        if hasattr(self, "driver"):
            self.driver.quit()


def scrape_website_multiple_viewports(
    url: str,
    viewports: list[tuple[int, int]],
    root_selector: str = "body",
    wait_time: float = 1.0,
    headless: bool = True,
) -> dict[str, Any]:
    """Convenience function to scrape a website at multiple viewport sizes.

    Args:
        url: URL to scrape
        viewports: List of (width, height) tuples for different viewport sizes
        root_selector: CSS selector for root element (default: "body")
        wait_time: Time to wait after each page load in seconds (default: 1.0)
        headless: Whether to run Chrome in headless mode (default: True)

    Returns:
        Dictionary with 'meta', 'examples', and 'captures' keys, compatible with
        Mockdown input format.

    Example:
        >>> viewports = [(320, 568), (768, 1024), (1920, 1080)]
        >>> result = scrape_website_multiple_viewports("https://example.com", viewports)
        >>> # result['examples'] contains 3 layout examples
    """
    scraper = MultiViewportScraper(headless=headless)
    try:
        return scraper.scrape_multiple_viewports(
            url, viewports, root_selector, wait_time
        )
    finally:
        scraper.cleanup()


def scrape_website_responsive_breakpoints(
    url: str,
    root_selector: str = "body",
    wait_time: float = 1.0,
    headless: bool = True,
    custom_viewports: list[tuple[int, int]] | None = None,
) -> dict[str, Any]:
    """Convenience function to scrape a website at common responsive breakpoints.

    Args:
        url: URL to scrape
        root_selector: CSS selector for root element (default: "body")
        wait_time: Time to wait after each page load in seconds (default: 1.0)
        headless: Whether to run Chrome in headless mode (default: True)
        custom_viewports: Optional custom list of (width, height) tuples to use instead

    Returns:
        Dictionary with 'meta', 'examples', and 'captures' keys

    Example:
        >>> result = scrape_website_responsive_breakpoints("https://example.com")
        >>> # result['examples'] contains 7 layout examples at different breakpoints
    """
    scraper = MultiViewportScraper(headless=headless)
    try:
        return scraper.scrape_responsive_breakpoints(
            url, root_selector, wait_time, custom_viewports
        )
    finally:
        scraper.cleanup()


def scrape_website_structured_viewports(
    url: str, root_selector: str = "body", wait_time: float = 1.0, headless: bool = True
) -> dict[str, Any]:
    """Convenience function to scrape a website with structured viewport sizes.

    Scrapes 10 viewport sizes: 3 regular, 3 flat/wide, 3 skinny/tall, 1 standard.

    Args:
        url: URL to scrape
        root_selector: CSS selector for root element (default: "body")
        wait_time: Time to wait after each page load in seconds (default: 1.0)
        headless: Whether to run Chrome in headless mode (default: True)

    Returns:
        Dictionary with 'meta', 'examples', and 'captures' keys

    Example:
        >>> result = scrape_website_structured_viewports("https://example.com")
        >>> # result['examples'] contains 10 layout examples with
              different aspect ratios
    """
    scraper = MultiViewportScraper(headless=headless)
    try:
        return scraper.scrape_structured_viewports(url, root_selector, wait_time)
    finally:
        scraper.cleanup()


def _extract_website_name(url: str) -> str:
    """Extract a clean website name from URL for use in directory names.

    Args:
        url: URL to parse

    Returns:
        Clean website name (e.g., "example.com" from "https://example.com/path")
        Uses dots as-is for readability, but safe for filesystem
    """
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split("/")[0]
    # Remove www. prefix if present
    if domain.startswith("www."):
        domain = domain[4:]
    # Remove port if present
    if ":" in domain:
        domain = domain.split(":")[0]
    # Keep dots but replace other invalid filename characters
    domain = domain.replace("/", "_").replace("\\", "_").replace(":", "_")
    return domain or "website"


def main():
    """Command-line entry point for the multi-viewport scraper."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Scrape a website at multiple viewport "
            "sizes to capture responsive layouts."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://example.com
  %(prog)s https://example.com output.json
  %(prog)s https://example.com --viewports 320,568 768,1024 1920,1080
  
By default, output is saved to src/cse291p/util/websites/<website-name>/scraped.json
        """,
    )

    parser.add_argument("url", help="URL to scrape")

    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help=(
            "Output JSON file (default: saved to "
            "src/cse291p/util/websites/<website-name>/scraped.json,"
            " or stdout if --stdout)"
        ),
    )

    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print output to stdout instead of saving to file",
    )

    parser.add_argument(
        "--root", default="body", help='CSS selector for root element (default: "body")'
    )

    parser.add_argument(
        "--wait-time",
        type=float,
        default=5.0,
        help=(
            "Time to wait after each page load in seconds "
            "(default: 5.0 for JavaScript-heavy pages)"
        ),
    )

    parser.add_argument(
        "--viewports",
        nargs="+",
        metavar="WIDTH,HEIGHT",
        help=(
            'Custom viewport sizes as "width,height" pairs (e.g., "320,568 768,1024"). '
            "If not specified, uses structured viewports "
            "(3 regular, 3 flat, 3 skinny, 1 standard)."
        ),
    )

    parser.add_argument(
        "--use-breakpoints",
        action="store_true",
        help=(
            "Use common responsive breakpoints instead of structured viewports "
            "(default: structured)"
        ),
    )

    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run Chrome in visible mode (default: headless)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set up logging
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    # Parse custom viewports if provided
    custom_viewports = None
    if args.viewports:
        try:
            custom_viewports = []
            for vp_str in args.viewports:
                parts = vp_str.split(",")
                if len(parts) != 2:
                    parser.error(
                        f'Invalid viewport format: {vp_str}. Expected "width,height"'
                    )
                width, height = int(parts[0]), int(parts[1])
                custom_viewports.append((width, height))
        except ValueError as e:
            parser.error(f"Invalid viewport format: {e}")

    # Scrape the website
    try:
        if custom_viewports:
            result = scrape_website_multiple_viewports(
                url=args.url,
                viewports=custom_viewports,
                root_selector=args.root,
                wait_time=args.wait_time,
                headless=not args.no_headless,
            )
        elif args.use_breakpoints:
            result = scrape_website_responsive_breakpoints(
                url=args.url,
                root_selector=args.root,
                wait_time=args.wait_time,
                headless=not args.no_headless,
                custom_viewports=None,
            )
        else:
            # Default: use structured viewports
            # (3 regular, 3 flat, 3 skinny, 1 standard)
            result = scrape_website_structured_viewports(
                url=args.url,
                root_selector=args.root,
                wait_time=args.wait_time,
                headless=not args.no_headless,
            )

        # Determine output path
        if args.stdout:
            # Print to stdout
            output_json = json.dumps(result, indent=2, ensure_ascii=False)
            print(output_json)
        elif args.output:
            # Use explicitly provided output path
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(
                f"Scraped {len(result['examples'])}"
                "viewport sizes and saved to {output_path}"
            )
        else:
            # Default: save to websites/<website-name>/<website-name>_scraped.json
            # Path calculation: from src/cse291p/util/multi_viewport_scraper.py
            # Save in the same directory as the scraper: src/cse291p/util/websites/
            website_name = _extract_website_name(args.url)
            util_dir = Path(__file__).parent  # src/cse291p/util/
            output_dir = util_dir / "websites" / website_name
            output_dir.mkdir(parents=True, exist_ok=True)
            # Use website name in filename for clarity
            output_filename = f"{website_name}_scraped.json"
            output_path = output_dir / output_filename

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(f"Scraped {len(result['examples'])} viewport sizes")
            print(f"Saved to: {output_path}")

        sys.exit(0)

    except KeyboardInterrupt:
        print("\nScraping interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
