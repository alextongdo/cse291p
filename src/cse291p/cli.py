"""Command-line interface for cse291p."""

import json
import logging
from pathlib import Path
from typing import List, Tuple

import click

from cse291p.scraping import Scraper
from cse291p.pipeline.run import synthesize, MockdownOptions

logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(verbose: bool):
    """cse291p - Constraint synthesis from layout examples."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


@cli.command()
@click.option('--url', '-u', required=True, help='URL to scrape')
@click.option('--output', '-o', type=click.Path(path_type=Path), required=True,
              help='Output JSON file path')
@click.option('--width', '-w', type=int, default=1920, help='Window width')
@click.option('--height', '-h', type=int, default=1080, help='Window height')
@click.option('--root-selector', default='body', help='CSS selector for root element')
@click.option('--wait', type=float, default=1.0, help='Wait time after page load (seconds)')
@click.option('--headless/--no-headless', default=True, help='Run browser in headless mode')
def scrape(url: str, output: Path, width: int, height: int, root_selector: str, 
           wait: float, headless: bool):
    """Scrape a single URL at a specific window size."""
    try:
        with Scraper(headless=headless) as scraper:
            result = scraper.scrape(url, (width, height), root_selector, wait)
            
            # Write output
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('w') as f:
                json.dump(result, f, indent=2)
            
            click.echo(f"✓ Scraped {url} at {width}x{height}")
            click.echo(f"✓ Saved to {output}")
            click.echo(f"  Found {len(result['examples'][0].get('children', []))} top-level children")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--url', '-u', required=True, help='URL to scrape')
@click.option('--output', '-o', type=click.Path(path_type=Path), required=True,
              help='Output JSON file path')
@click.option('--sizes', multiple=True, type=(int, int), 
              default=[(1920, 1080), (1200, 800), (768, 1024), (375, 667)],
              help='Screen sizes as WIDTH HEIGHT (can specify multiple times)')
@click.option('--root-selector', default='body', help='CSS selector for root element')
@click.option('--wait', type=float, default=1.0, help='Wait time after page load (seconds)')
@click.option('--headless/--no-headless', default=True, help='Run browser in headless mode')
def scrape_responsive(url: str, output: Path, sizes: List[Tuple[int, int]], 
                      root_selector: str, wait: float, headless: bool):
    """Scrape a URL at multiple screen sizes for responsive layout testing.
    
    Example:
        cse291p scrape-responsive -u https://example.com -o output.json \\
            --sizes 1920 1080 --sizes 768 1024 --sizes 375 667
    """
    try:
        with Scraper(headless=headless) as scraper:
            result = scraper.scrape_responsive(url, list(sizes), root_selector, wait)
            
            # Write output
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('w') as f:
                json.dump(result, f, indent=2)
            
            click.echo(f"✓ Scraped {url} at {len(sizes)} screen sizes")
            click.echo(f"✓ Saved to {output}")
            click.echo(f"  Collected {len(result['examples'])} layout examples")
            
            # Show breakdown by screen size
            for i, meta in enumerate(result['meta']['screen_sizes']):
                example = result['examples'][i]
                children_count = len(example.get('children', []))
                click.echo(f"  {meta['width']}x{meta['height']}: {children_count} top-level children")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--input-file', '-i', type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True,
              help='Path to JSON input. For default format, expects {"examples": [...]} with default records. For bench, {"train": [...]}')
@click.option('--input-format', type=click.Choice(['default', 'bench']), default='default')
@click.option('--numeric-type', type=click.Choice(['N', 'R', 'Q', 'Z']), default='N')
@click.option('--instantiation-method', type=click.Choice(['numpy', 'prolog']), default='numpy')
@click.option('--learning-method', type=click.Choice(['simple', 'heuristic', 'noisetolerant']), default='noisetolerant')
@click.option('--unambig/--no-unambig', default=False, help='Synthesize unambiguous layout (stronger).')
@click.option('--output-file', '-o', type=click.Path(path_type=Path), help='Output JSON file (default: print to stdout)')
def synthesize_cmd(input_file: Path, input_format: str, numeric_type: str, 
                   instantiation_method: str, learning_method: str, unambig: bool,
                   output_file: Path):
    """Run constraint synthesis pipeline from a JSON input file."""
    try:
        with input_file.open('r') as fh:
            input_data = json.load(fh)
        
        options: MockdownOptions = {
            'input_format': input_format,
            'numeric_type': numeric_type,
            'instantiation_method': instantiation_method,
            'learning_method': learning_method,
            'unambig': unambig,
        }
        
        output = synthesize(input_data, options)
        output_json = json.dumps(output, indent=2)
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with output_file.open('w') as f:
                f.write(output_json)
            click.echo(f"✓ Synthesis complete. Output saved to {output_file}")
        else:
            click.echo(output_json)
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    cli()
