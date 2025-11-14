"""List available auto-mock benchmarks and their structure.

This script analyzes the auto-mock benchmark cache to show what benchmarks
are available for testing our evaluation metrics.
"""

import json
from pathlib import Path
from collections import defaultdict


def analyze_benchmark(bench_path: Path) -> dict:
    """Analyze a benchmark file and return statistics."""
    with bench_path.open('r') as f:
        data = json.load(f)
    
    train = data.get("train", [])
    test = data.get("test", [])
    
    def count_views(view):
        """Count total views in hierarchy."""
        count = 1
        for child in view.get("children", []):
            count += count_views(child)
        return count
    
    def get_max_depth(view, depth=0):
        """Get maximum depth of view hierarchy."""
        if not view.get("children"):
            return depth
        return max(get_max_depth(child, depth + 1) for child in view.get("children", []))
    
    train_stats = {
        "count": len(train),
        "total_views": sum(count_views(v) for v in train) if train else 0,
        "max_depth": max(get_max_depth(v) for v in train) if train else 0,
        "avg_views_per_example": sum(count_views(v) for v in train) / len(train) if train else 0,
    }
    
    test_stats = {
        "count": len(test),
        "total_views": sum(count_views(v) for v in test) if test else 0,
    }
    
    bench_info = data.get("bench", {})
    width_range = bench_info.get("width", {})
    height_range = bench_info.get("height", {})
    
    return {
        "name": bench_path.stem,
        "train": train_stats,
        "test": test_stats,
        "width_range": f"{width_range.get('low', '?')}-{width_range.get('high', '?')}",
        "height_range": f"{height_range.get('low', '?')}-{height_range.get('high', '?')}",
    }


def main():
    """List all available benchmarks."""
    auto_mock_dir = Path(__file__).parent.parent / "auto-mock" / "bench_cache"
    
    if not auto_mock_dir.exists():
        print(f"Error: auto-mock directory not found at {auto_mock_dir}")
        return
    
    benchmark_files = sorted(auto_mock_dir.glob("*.json"))
    benchmark_files = [f for f in benchmark_files if not f.name.startswith("old")]
    
    if not benchmark_files:
        print(f"No benchmark files found in {auto_mock_dir}")
        return
    
    print(f"Found {len(benchmark_files)} benchmark files in auto-mock/bench_cache\n")
    print("=" * 100)
    print(f"{'Benchmark':<30} {'Train':<8} {'Test':<8} {'Views/Ex':<10} {'Depth':<6} {'Width Range':<15} {'Height Range':<15}")
    print("=" * 100)
    
    # Group by category
    categories = defaultdict(list)
    for bench_file in benchmark_files:
        name = bench_file.stem
        if "-" in name:
            category = name.split("-")[0]
        else:
            category = "other"
        categories[category].append(bench_file)
    
    all_stats = []
    for category in sorted(categories.keys()):
        print(f"\n{category.upper()}:")
        for bench_file in sorted(categories[category]):
            try:
                stats = analyze_benchmark(bench_file)
                all_stats.append(stats)
                print(f"  {stats['name']:<28} {stats['train']['count']:<8} {stats['test']['count']:<8} "
                      f"{stats['train']['avg_views_per_example']:<10.1f} {stats['train']['max_depth']:<6} "
                      f"{stats['width_range']:<15} {stats['height_range']:<15}")
            except Exception as e:
                print(f"  {bench_file.stem:<28} ERROR: {e}")
    
    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Total benchmarks: {len(all_stats)}")
    print(f"Total train examples: {sum(s['train']['count'] for s in all_stats)}")
    print(f"Total test examples: {sum(s['test']['count'] for s in all_stats)}")
    print(f"Average views per example: {sum(s['train']['avg_views_per_example'] for s in all_stats) / len(all_stats):.1f}")
    print(f"Max hierarchy depth: {max(s['train']['max_depth'] for s in all_stats)}")
    
    # Recommended benchmarks for testing
    print("\n" + "=" * 100)
    print("RECOMMENDED BENCHMARKS FOR TESTING")
    print("=" * 100)
    print("\nSimple benchmarks (good for initial testing):")
    simple = [s for s in all_stats if s['train']['avg_views_per_example'] < 5 and s['train']['max_depth'] <= 2]
    for s in sorted(simple, key=lambda x: x['train']['avg_views_per_example'])[:10]:
        print(f"  - {s['name']:<30} ({s['train']['avg_views_per_example']:.1f} views/ex, depth {s['train']['max_depth']})")
    
    print("\nMedium complexity benchmarks:")
    medium = [s for s in all_stats if 5 <= s['train']['avg_views_per_example'] < 20]
    for s in sorted(medium, key=lambda x: x['train']['avg_views_per_example'])[:10]:
        print(f"  - {s['name']:<30} ({s['train']['avg_views_per_example']:.1f} views/ex, depth {s['train']['max_depth']})")
    
    print("\nComplex benchmarks (real-world websites):")
    complex_bench = [s for s in all_stats if s['train']['avg_views_per_example'] >= 20]
    for s in sorted(complex_bench, key=lambda x: x['train']['avg_views_per_example'], reverse=True)[:10]:
        print(f"  - {s['name']:<30} ({s['train']['avg_views_per_example']:.1f} views/ex, depth {s['train']['max_depth']})")


if __name__ == '__main__':
    main()

