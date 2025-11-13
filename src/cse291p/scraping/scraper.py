"""Web scraping utilities for extracting layout data from websites.

Reimplements: mockdown/src/mockdown/scraping/scraper.py
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import WebDriverException, TimeoutException

logger = logging.getLogger(__name__)

# Exclusions taken from Tree.js in auto-mock.
# These selectors are excluded from scraping as they typically contain
# text content rather than layout structure.
DEFAULT_EXCLUDED_SELECTORS = [
    'p > *',
    'h1 > *',
    'h2 > *',
    'h3 > *',
    'h4 > *',
    'h5 > *',
    'h6 > *',
    'select > *'
]

# JavaScript payload that extracts DOM structure and bounding boxes
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
                rect.right + window.scrollX,
                rect.bottom + window.scrollY
            ]           
        };
        return data;
    }
    
    return scrape(rootElement, undefined);
"""

SANITIZED_KEY_ORDER = ('name', 'rect', 'children')


class Scraper:
    """Web scraper for extracting layout data from websites.
    
    Uses Selenium to load web pages and extract DOM structure with bounding boxes.
    Supports scraping at different window sizes to capture responsive layouts.
    """
    
    def __init__(self, headless: bool = True, wait_time: int = 5):
        """Initialize the scraper.
        
        Args:
            headless: Whether to run Chrome in headless mode
            wait_time: Implicit wait time in seconds for page loads
        """
        self.headless = headless
        self.wait_time = wait_time
        self.driver: Optional[webdriver.Chrome] = None
        self._initialize_driver()
    
    def _initialize_driver(self) -> None:
        """Initialize the Chrome WebDriver."""
        try:
            opts = ChromeOptions()
            if self.headless:
                opts.add_argument('--headless')
            opts.add_argument('--no-sandbox')
            opts.add_argument('--disable-dev-shm-usage')
            opts.add_argument('--disable-gpu')
            opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
            
            # Use Service for Selenium 4.x compatibility
            self.driver = webdriver.Chrome(options=opts)
            self.driver.implicitly_wait(self.wait_time)
            self.driver.set_window_size(1920, 1080)
            
            logger.info("Chrome WebDriver initialized successfully")
        except WebDriverException as e:
            logger.error(
                "Failed to initialize Chrome WebDriver. "
                "Make sure Chrome and chromedriver are installed and in PATH."
            )
            raise e
    
    def scrape(
        self,
        url: str,
        dims: Tuple[int, int],
        root_selector: str = "body",
        wait_after_load: float = 1.0
    ) -> Dict[str, Any]:
        """Scrape a single URL at a specific window size.
        
        Args:
            url: URL to scrape
            dims: Window dimensions as (width, height)
            root_selector: CSS selector for the root element to scrape
            wait_after_load: Seconds to wait after page load for dynamic content
        
        Returns:
            Dictionary with 'examples', 'meta', and 'captures' keys
        """
        if self.driver is None:
            raise RuntimeError("Driver not initialized. Call _initialize_driver() first.")
        
        width, height = dims
        
        try:
            logger.info(f"Scraping {url} at {width}x{height}")
            self.driver.set_window_size(width, height)
            self.driver.get(url)
            
            # Wait for page to load and dynamic content to render
            import time
            time.sleep(wait_after_load)
            
            # Find root element using modern Selenium 4.x API
            el = self.driver.find_element(By.CSS_SELECTOR, root_selector)
            
            # Execute JavaScript to extract layout data
            data = self.driver.execute_script(PAYLOAD, el, DEFAULT_EXCLUDED_SELECTORS)
            
            # Get screenshot
            screenshot = "data:image/png;base64," + self.driver.get_screenshot_as_base64()
            
            # Clean and format the output
            cleaned_data = self.clean_output(data)
            
            result = {
                'meta': {
                    'scrape': {
                        'origin': url,
                        'width': width,
                        'height': height,
                    }
                },
                'examples': [cleaned_data],
                'captures': [screenshot]
            }
            
            logger.info(f"Successfully scraped {url}: {len(cleaned_data.get('children', []))} top-level children")
            return result
            
        except TimeoutException as e:
            logger.error(f"Timeout while loading {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            raise
        finally:
            # Log browser console messages
            try:
                for entry in self.driver.get_log('browser'):
                    if entry.get('source') == 'console-api':
                        logger.debug(f"Browser console: {entry.get('message')}")
            except Exception:
                pass  # Ignore logging errors
    
    def scrape_responsive(
        self,
        url: str,
        screen_sizes: List[Tuple[int, int]],
        root_selector: str = "body",
        wait_after_load: float = 1.0
    ) -> Dict[str, Any]:
        """Scrape a URL at multiple screen sizes for responsive layout testing.
        
        Args:
            url: URL to scrape
            screen_sizes: List of (width, height) tuples for different screen sizes
            root_selector: CSS selector for the root element to scrape
            wait_after_load: Seconds to wait after each page load
        
        Returns:
            Dictionary with combined 'examples' from all screen sizes, plus metadata
        """
        all_examples = []
        all_captures = []
        all_meta = []
        
        for width, height in screen_sizes:
            try:
                result = self.scrape(url, (width, height), root_selector, wait_after_load)
                all_examples.extend(result['examples'])
                all_captures.extend(result['captures'])
                all_meta.append(result['meta']['scrape'])
            except Exception as e:
                logger.warning(f"Failed to scrape at {width}x{height}: {e}")
                continue
        
        return {
            'examples': all_examples,
            'meta': {
                'url': url,
                'screen_sizes': all_meta
            },
            'captures': all_captures
        }
    
    def clean_output(self, data: Dict[str, Any], order: Tuple[str, ...] = SANITIZED_KEY_ORDER) -> Dict[str, Any]:
        """Recursively reorder keys in output JSON.
        
        Puts 'children' last for better readability. Contents remain unchanged.
        
        Args:
            data: Raw scraped data dictionary
            order: Desired key order
        
        Returns:
            Cleaned data with reordered keys
        """
        if not isinstance(data, dict):
            return data
        
        return {
            k: [self.clean_output(c, order) for c in data[k]] if k == 'children' else data[k]
            for k in order
            if k in data
        }
    
    def cleanup(self) -> None:
        """Clean up and close the WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.cleanup()
        return False
