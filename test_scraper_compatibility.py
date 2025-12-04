#!/usr/bin/env python3
"""Test script to verify scraper compatibility with original Mockdown solver.

Run with: uv run python test_scraper_compatibility.py
"""

import json
import sys
from pathlib import Path

# Add mockdown to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'mockdown' / 'src'))

def test_scraped_data_with_mockdown():
    """Test our scraped IEEE data with original Mockdown solver."""
    print("=" * 80)
    print("TESTING SCRAPED DATA WITH ORIGINAL MOCKDOWN SOLVER")
    print("=" * 80)
    
    # Load our scraped IEEE data
    scraped_path = project_root / 'src' / 'cse291p' / 'util' / 'websites' / 'ieeexplore.ieee.org' / 'ieeexplore.ieee.org_scraped.json'
    
    if not scraped_path.exists():
        print(f"✗ Scraped data not found: {scraped_path}")
        return False
    
    with scraped_path.open() as f:
        scraped_data = json.load(f)
    
    print(f"\n✓ Loaded scraped data: {len(scraped_data['examples'])} examples")
    print(f"  First example root: {scraped_data['examples'][0]['name']}")
    print(f"  First example rect: {scraped_data['examples'][0]['rect']}")
    
    # Check coordinate consistency
    print("\n" + "-" * 80)
    print("Checking coordinate consistency...")
    
    def check_view(view, path=""):
        issues = []
        left, top, right, bottom = view['rect']
        width = right - left
        height = bottom - top
        
        if width < 0:
            issues.append(f"{path}{view['name']}: Negative width {width}")
        if height < 0:
            issues.append(f"{path}{view['name']}: Negative height {height}")
        if left < 0:
            issues.append(f"{path}{view['name']}: Negative left {left}")
        if top < 0:
            issues.append(f"{path}{view['name']}: Negative top {top}")
        
        for child in view.get('children', []):
            issues.extend(check_view(child, f"{path}{view['name']}/"))
        
        return issues
    
    all_issues = []
    for i, example in enumerate(scraped_data['examples'][:3]):
        issues = check_view(example, f"example[{i}]/")
        all_issues.extend(issues)
    
    if all_issues:
        print(f"✗ Found {len(all_issues)} coordinate issues:")
        for issue in all_issues[:10]:
            print(f"    {issue}")
        if len(all_issues) > 10:
            print(f"    ... and {len(all_issues) - 10} more")
        return False
    else:
        print("✓ All coordinates are consistent (no negative widths/heights)")
    
    # Test with Mockdown
    print("\n" + "-" * 80)
    print("Testing with original Mockdown solver...")
    
    # Prepare input for Mockdown (use first 3 examples for testing)
    test_data = {
        "examples": scraped_data['examples'][:3]
    }
    
    print(f"  Using {len(test_data['examples'])} examples")
    
    try:
        from mockdown.run import run
        
        print("  Running Mockdown pipeline...")
        result = run(
            input_data=test_data,
            options={
                "input_format": "default",
                "numeric_type": "N",
                "instantiation_method": "numpy",
                "learning_method": "noisetolerant",
                "pruning_method": "hierarchical",
                "pruning_bounds": (None, None, None, None),
                "include_axioms": False,
                "debug": False,
                "unambig": False,
            }
        )
        
        print(f"\n✓ Solver succeeded!")
        print(f"  Constraints: {len(result.get('constraints', []))}")
        print(f"  Axioms: {len(result.get('axioms', []))}")
        
        if result.get('constraints'):
            print(f"\n  Sample constraints:")
            for constraint in result['constraints'][:5]:
                print(f"    {constraint}")
        
        return True
        
    except ImportError as e:
        print(f"\n✗ Import error: {e}")
        print("  Make sure you're in the correct conda environment:")
        print("    conda activate fifteenAI")
        return False
    except Exception as e:
        print(f"\n✗ Solver failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bench_format_conversion():
    """Test conversion to bench format."""
    print("\n" + "=" * 80)
    print("TESTING BENCH FORMAT CONVERSION")
    print("=" * 80)
    
    scraped_path = project_root / 'src' / 'cse291p' / 'util' / 'websites' / 'ieeexplore.ieee.org' / 'ieeexplore.ieee.org_scraped.json'
    
    if not scraped_path.exists():
        print(f"✗ Scraped data not found: {scraped_path}")
        return False
    
    with scraped_path.open() as f:
        scraped_data = json.load(f)
    
    # Convert to bench format
    print("\nConverting to bench format...")
    
    def convert_view_to_bench(view):
        left, top, right, bottom = view['rect']
        bench_view = {
            "name": view["name"],
            "top": top,
            "left": left,
            "width": right - left,
            "height": bottom - top,
        }
        if "children" in view and view["children"]:
            bench_view["children"] = [convert_view_to_bench(child) for child in view["children"]]
        return bench_view
    
    bench_data = {
        "train": [convert_view_to_bench(ex) for ex in scraped_data['examples'][:3]]
    }
    
    print(f"✓ Converted {len(bench_data['train'])} examples to bench format")
    print(f"  First example: {bench_data['train'][0]['name']}")
    print(f"    top={bench_data['train'][0]['top']}, left={bench_data['train'][0]['left']}")
    print(f"    width={bench_data['train'][0]['width']}, height={bench_data['train'][0]['height']}")
    
    # Test with Mockdown using bench format
    print("\nTesting with Mockdown using bench format...")
    
    try:
        from mockdown.run import run
        
        result = run(
            input_data=bench_data,
            options={
                "input_format": "bench",
                "numeric_type": "N",
                "instantiation_method": "numpy",
                "learning_method": "noisetolerant",
                "pruning_method": "hierarchical",
                "pruning_bounds": (None, None, None, None),
                "include_axioms": False,
                "debug": False,
                "unambig": False,
            }
        )
        
        print(f"\n✓ Solver succeeded with bench format!")
        print(f"  Constraints: {len(result.get('constraints', []))}")
        return True
        
    except Exception as e:
        print(f"\n✗ Solver failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n")
    success1 = test_scraped_data_with_mockdown()
    success2 = test_bench_format_conversion()
    
    print("\n" + "=" * 80)
    if success1 and success2:
        print("✓ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        sys.exit(1)

