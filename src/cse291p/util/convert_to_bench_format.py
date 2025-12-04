"""Utility to convert scraped data to Mockdown's 'bench' format.

The original Mockdown paper used 'bench' format examples with:
  {top, left, width, height} fields

Our scraper outputs 'default' format with:
  rect: [left, top, right, bottom]

This utility converts between formats for compatibility.
"""

import json
from pathlib import Path
from typing import Any, Dict, List


def convert_rect_to_bench_format(rect: List[float]) -> Dict[str, float]:
    """Convert rect [left, top, right, bottom] to bench format {top, left, width, height}.
    
    Args:
        rect: [left, top, right, bottom] in document coordinates
        
    Returns:
        Dictionary with top, left, width, height
    """
    left, top, right, bottom = rect
    return {
        "top": top,
        "left": left,
        "width": right - left,
        "height": bottom - top,
    }


def convert_view_to_bench_format(view: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively convert a view from default format to bench format.
    
    Args:
        view: View dict with 'rect' field in default format
        
    Returns:
        View dict with 'top', 'left', 'width', 'height' fields in bench format
    """
    bench_view = {
        "name": view["name"],
        **convert_rect_to_bench_format(view["rect"]),
    }
    
    if "children" in view and view["children"]:
        bench_view["children"] = [
            convert_view_to_bench_format(child) for child in view["children"]
        ]
    
    return bench_view


def convert_scraped_to_bench_format(
    scraped_data: Dict[str, Any], output_path: Path | None = None
) -> Dict[str, Any]:
    """Convert scraped data from default format to bench format.
    
    Args:
        scraped_data: Scraped data dict with 'examples' in default format
        output_path: Optional path to save converted data
        
    Returns:
        Dict with 'train' key containing bench-format examples
    """
    examples = scraped_data.get("examples", [])
    
    bench_examples = [convert_view_to_bench_format(ex) for ex in examples]
    
    result = {
        "train": bench_examples,
        # Preserve metadata if present
        "meta": scraped_data.get("meta", {}),
    }
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Converted {len(bench_examples)} examples to bench format")
        print(f"Saved to: {output_path}")
    
    return result


def verify_coordinate_consistency(view: Dict[str, Any], path: str = "") -> List[str]:
    """Verify that a view's coordinates are consistent (no negative widths/heights).
    
    Args:
        view: View dict (either default or bench format)
        path: Path string for error reporting
        
    Returns:
        List of error messages (empty if all checks pass)
    """
    errors = []
    
    if "rect" in view:
        # Default format: rect: [left, top, right, bottom]
        left, top, right, bottom = view["rect"]
        width = right - left
        height = bottom - top
    elif "left" in view and "top" in view and "width" in view and "height" in view:
        # Bench format: {top, left, width, height}
        left = view["left"]
        top = view["top"]
        width = view["width"]
        height = view["height"]
        right = left + width
        bottom = top + height
    else:
        errors.append(f"{path}{view.get('name', 'unknown')}: Unknown format")
        return errors
    
    if width < 0:
        errors.append(f"{path}{view.get('name', 'unknown')}: Negative width {width}")
    if height < 0:
        errors.append(f"{path}{view.get('name', 'unknown')}: Negative height {height}")
    if left < 0:
        errors.append(f"{path}{view.get('name', 'unknown')}: Negative left {left}")
    if top < 0:
        errors.append(f"{path}{view.get('name', 'unknown')}: Negative top {top}")
    
    # Check children recursively
    for child in view.get("children", []):
        child_path = f"{path}{view.get('name', 'unknown')}/"
        errors.extend(verify_coordinate_consistency(child, child_path))
    
    return errors


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert scraped data to Mockdown bench format"
    )
    parser.add_argument("input", help="Input JSON file (scraped data in default format)")
    parser.add_argument(
        "output", nargs="?", help="Output JSON file (default: input with _bench suffix)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify coordinate consistency after conversion",
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        exit(1)
    
    with open(input_path) as f:
        scraped_data = json.load(f)
    
    output_path = Path(args.output) if args.output else input_path.with_suffix("_bench.json")
    
    bench_data = convert_scraped_to_bench_format(scraped_data, output_path)
    
    if args.verify:
        print("\nVerifying coordinate consistency...")
        errors = []
        for i, example in enumerate(bench_data["train"]):
            ex_errors = verify_coordinate_consistency(example, f"example[{i}]/")
            errors.extend(ex_errors)
        
        if errors:
            print(f"\nFound {len(errors)} coordinate issues:")
            for error in errors[:20]:  # Show first 20
                print(f"  {error}")
            if len(errors) > 20:
                print(f"  ... and {len(errors) - 20} more")
        else:
            print("✓ All coordinates are consistent (no negative widths/heights)")

