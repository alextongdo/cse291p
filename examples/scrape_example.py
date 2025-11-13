"""Example script demonstrating how to use the web scraper.

This script shows how to:
1. Scrape a single URL at a specific window size
2. Scrape a URL at multiple screen sizes for responsive layout testing
3. Use the scraped data with the constraint synthesis pipeline
"""

import json
from pathlib import Path

from cse291p.scraping import Scraper


def example_single_scrape():
    """Example: Scrape a single URL at one window size."""
    print("Example 1: Single scrape")
    print("-" * 50)
    
    with Scraper(headless=True) as scraper:
        # Scrape Bootstrap grid example at desktop size
        result = scraper.scrape(
            url="https://getbootstrap.com/docs/5.3/layout/grid/",
            dims=(1920, 1080),
            root_selector="body",
            wait_after_load=2.0  # Wait 2 seconds for page to fully load
        )
        
        # Save to file
        output_file = Path("outputs/scraped_bootstrap.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open('w') as f:
            json.dump(result, f, indent=2)
        
        print(f"✓ Scraped {len(result['examples'])} example(s)")
        print(f"✓ Saved to {output_file}")
        print(f"  Top-level children: {len(result['examples'][0].get('children', []))}")


def example_responsive_scrape():
    """Example: Scrape a URL at multiple screen sizes for responsive testing."""
    print("\nExample 2: Responsive scrape")
    print("-" * 50)
    
    # Define screen sizes to test
    screen_sizes = [
        (1920, 1080),  # Large desktop
        (1200, 800),   # Medium desktop
        (768, 1024),   # Tablet
        (375, 667),    # Mobile
    ]
    
    with Scraper(headless=True) as scraper:
        # Scrape at multiple sizes
        result = scraper.scrape_responsive(
            url="https://getbootstrap.com/docs/5.3/layout/grid/",
            screen_sizes=screen_sizes,
            root_selector="body",
            wait_after_load=2.0
        )
        
        # Save to file
        output_file = Path("outputs/scraped_responsive.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open('w') as f:
            json.dump(result, f, indent=2)
        
        print(f"✓ Scraped {len(result['examples'])} examples")
        print(f"✓ Saved to {output_file}")
        
        # Show breakdown by screen size
        for i, meta in enumerate(result['meta']['screen_sizes']):
            example = result['examples'][i]
            children_count = len(example.get('children', []))
            print(f"  {meta['width']}x{meta['height']}: {children_count} top-level children")


def example_use_with_pipeline():
    """Example: Use scraped data with the constraint synthesis pipeline."""
    print("\nExample 3: Using scraped data with pipeline")
    print("-" * 50)
    
    # First, scrape some data
    with Scraper(headless=True) as scraper:
        result = scraper.scrape_responsive(
            url="https://getbootstrap.com/docs/5.3/layout/grid/",
            screen_sizes=[(1920, 1080), (768, 1024), (375, 667)],
            wait_after_load=2.0
        )
    
    # The scraped data is already in the format expected by the pipeline!
    # Just extract the 'examples' array
    pipeline_input = {
        "examples": result["examples"]
    }
    
    # Save in pipeline format
    output_file = Path("outputs/pipeline_input.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open('w') as f:
        json.dump(pipeline_input, f, indent=2)
    
    print(f"✓ Prepared pipeline input with {len(pipeline_input['examples'])} examples")
    print(f"✓ Saved to {output_file}")
    print("\n  You can now run the pipeline with:")
    print(f"  python -m cse291p synthesize -i {output_file}")


if __name__ == "__main__":
    print("Web Scraper Examples")
    print("=" * 50)
    print("\nNote: These examples require:")
    print("  1. Chrome browser installed")
    print("  2. chromedriver in PATH")
    print("  3. selenium package installed (pip install selenium)")
    print("  4. Internet connection")
    print()
    
    try:
        # Uncomment the example you want to run:
        # example_single_scrape()
        # example_responsive_scrape()
        # example_use_with_pipeline()
        
        print("\nUncomment an example function to run it!")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure you have Chrome and chromedriver installed.")

