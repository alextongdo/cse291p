import argparse
import json

from src.evaluation import calculate_rmsd
from src.main import Mockdown
from src.types import View


def main():
    parser = argparse.ArgumentParser(description="Run Mockdown benchmark on a dataset")
    parser.add_argument("input", help="Path to bench JSON file (rect format)")
    parser.add_argument(
        "--visualize", action="store_true", help="Visualize predictions"
    )
    args = parser.parse_args()

    # Load data
    with open(args.input) as f:
        data = json.load(f)

    train_data = data["train"]
    test_data = data["test"]

    print(f"Dataset: {data.get('name', 'unknown')}")
    print(f"Train examples: {len(train_data)}")
    print(f"Test examples: {len(test_data)}")
    print()

    # Train
    train_views = [View(**example) for example in train_data]
    mockdown = Mockdown()
    # mockdown = ConditionalMockdown()
    mockdown.fit(train_views)

    # Evaluate on each test example
    rmsds: list[float] = []

    print("Test Results:")
    print("-" * 50)

    for i, test_example in enumerate(test_data):
        test_view = View(**test_example)
        width = int(test_view.width)
        height = int(test_view.height)

        predicted = mockdown.predict(width, height)
        rmsd = calculate_rmsd(predicted, test_view)
        rmsds.append(rmsd)

        print(f"  Test {i}: size=({width}, {height}), RMSD={rmsd:.4f}")

        if args.visualize:
            from src.visualize import visualize

            visualize(predicted, root_name="root")

    print("-" * 50)
    avg_rmsd = sum(rmsds) / len(rmsds) if rmsds else 0.0
    print(f"Average RMSD: {avg_rmsd:.4f}")


if __name__ == "__main__":
    main()
