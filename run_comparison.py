import argparse
import json

from src.evaluation import calculate_accuracy, calculate_rmsd
from src.main import ConditionalMockdown, Mockdown
from src.types import LinearConstraint, View


def format_constraint(c: LinearConstraint) -> str:
    """Format a constraint for display."""
    if c.x is None:
        return f"{c.y.view.name}.{c.y.type} = {c.b}"
    return f"{c.y.view.name}.{c.y.type} = {c.a} * {c.x.view.name}.{c.x.type} + {c.b}"


def main():
    parser = argparse.ArgumentParser(
        description="Compare Mockdown vs ConditionalMockdown constraints"
    )
    parser.add_argument("input", help="Path to JSON file with examples")
    parser.add_argument(
        "--width", type=int, default=None, help="Test width (default: first example)"
    )
    parser.add_argument(
        "--height", type=int, default=None, help="Test height (default: first example)"
    )
    args = parser.parse_args()

    # Load data
    with open(args.input) as f:
        data = json.load(f)

    # Handle both formats: raw list or {"train": [...]} or {"examples": [...]}
    if isinstance(data, list):
        examples_data = data
    elif "train" in data:
        examples_data = data["train"]
    elif "examples" in data:
        examples_data = data["examples"]
    else:
        examples_data = data

    print(f"Loaded {len(examples_data)} examples")

    views = [View(**example) for example in examples_data]

    # Default test size from first example
    test_width = args.width or int(views[0].width)
    test_height = args.height or int(views[0].height)

    print(f"Test size: ({test_width}, {test_height})")
    print()

    # Run original Mockdown
    print("=" * 60)
    print("ORIGINAL MOCKDOWN")
    print("=" * 60)
    mockdown = Mockdown()
    mockdown.fit(views)

    original_constraints = set(mockdown.constraints)
    print(f"Total constraints: {len(original_constraints)}")
    print()
    print("Constraints:")
    for c in sorted(original_constraints, key=format_constraint):
        print(f"  {format_constraint(c)}")
    print()

    # Run ConditionalMockdown
    print("=" * 60)
    print("CONDITIONAL MOCKDOWN")
    print("=" * 60)
    cond_mockdown = ConditionalMockdown()
    cond_mockdown.fit(views)

    # Show constraints per group
    print("Constraints by group:")
    for group_key, constraints in sorted(cond_mockdown.ex_to_constrs_map.items()):
        print(f"  Group {group_key}: {len(constraints)} constraints")
        for c in constraints:
            print(f"    {format_constraint(c)}")
    print()

    # Get constraints that would be used for test size
    from bisect import bisect_left

    sorted_indices = sorted(range(len(views)), key=lambda i: views[i].width)
    sorted_widths = [views[i].width for i in sorted_indices]
    midpoints = [
        (sorted_widths[i] + sorted_widths[i + 1]) / 2
        for i in range(len(sorted_widths) - 1)
    ]
    selected_idx = sorted_indices[bisect_left(midpoints, test_width)]

    print(
        f"For test width {test_width}, selected example "
        f"{selected_idx} (width={views[selected_idx].width})"
    )

    # Collect constraints for the selected example
    conditional_constraints: set[LinearConstraint] = set()
    for group_key, constraints in cond_mockdown.ex_to_constrs_map.items():
        if selected_idx in group_key:
            conditional_constraints.update(constraints)

    print(f"Total constraints for this size: {len(conditional_constraints)}")
    print()

    # Compare
    print("=" * 60)
    print("COMPARISON")
    print("=" * 60)

    only_original = original_constraints - conditional_constraints
    only_conditional = conditional_constraints - original_constraints
    common = original_constraints & conditional_constraints

    print(f"Common constraints: {len(common)}")
    print(f"Only in Original: {len(only_original)}")
    print(f"Only in Conditional: {len(only_conditional)}")
    print()

    if only_original:
        print("Only in Original:")
        for c in sorted(only_original, key=format_constraint):
            print(f"  {format_constraint(c)}")
        print()

    if only_conditional:
        print("Only in Conditional:")
        for c in sorted(only_conditional, key=format_constraint):
            print(f"  {format_constraint(c)}")
    print()

    # RMSD Comparison
    print("=" * 60)
    print("RMSD COMPARISON")
    print("=" * 60)

    # Use first example as ground truth
    ground_truth = views[0]
    print(
        f"Ground truth:{ground_truth.name} ({ground_truth.width}x{ground_truth.height})"
    )
    print()

    # Predict with original Mockdown
    original_predicted = None
    original_rmsd = None
    try:
        original_predicted = mockdown.predict(test_width, test_height)
        original_rmsd = calculate_rmsd(original_predicted, ground_truth)
        print(f"Original Mockdown RMSD: {original_rmsd:.4f}")
    except Exception as e:
        print(f"Original Mockdown prediction failed: {e}")

    # Predict with ConditionalMockdown
    conditional_predicted = None
    conditional_rmsd = None
    try:
        conditional_predicted = cond_mockdown.predict(test_width, test_height)
        conditional_rmsd = calculate_rmsd(conditional_predicted, ground_truth)
        print(f"Conditional Mockdown RMSD: {conditional_rmsd:.4f}")
    except Exception as e:
        print(f"Conditional Mockdown prediction failed: {e}")

    # Compare RMSD
    if original_rmsd is not None and conditional_rmsd is not None:
        diff = conditional_rmsd - original_rmsd
        print()
        if abs(diff) < 0.0001:
            print("RMSDs are effectively equal")
        elif diff > 0:
            print(f"Original is better by {diff:.4f}")
        else:
            print(f"Conditional is better by {-diff:.4f}")

    # Accuracy Comparison
    print()
    print("=" * 60)
    print("ACCURACY COMPARISON")
    print("=" * 60)

    # Accuracy with original Mockdown
    if original_predicted is not None:
        original_acc = calculate_accuracy(original_predicted, ground_truth)
        print(f"Original Mockdown Accuracy: {original_acc:.2%}")
    else:
        original_acc = None

    # Accuracy with ConditionalMockdown
    if conditional_predicted is not None:
        conditional_acc = calculate_accuracy(conditional_predicted, ground_truth)
        print(f"Conditional Mockdown Accuracy: {conditional_acc:.2%}")
    else:
        conditional_acc = None

    # Compare Accuracy
    if original_acc is not None and conditional_acc is not None:
        diff = conditional_acc - original_acc
        print()
        if abs(diff) < 0.0001:
            print("Accuracies are effectively equal")
        elif diff > 0:
            print(f"Conditional is better by {diff:.2%}")
        else:
            print(f"Original is better by {-diff:.2%}")


if __name__ == "__main__":
    main()
