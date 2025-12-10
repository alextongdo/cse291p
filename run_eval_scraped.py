import json
import shutil
from pathlib import Path
from statistics import mean

from src.evaluation import calculate_accuracy, calculate_rmsd
from src.main import ConditionalMockdown, Mockdown
from src.types import View
from src.visualize import visualize

DATA_DIR = Path("data/generated")
TMP_DIR = Path("tmp_html")
TMP_DIR.mkdir(exist_ok=True)


def visualize_one(view: View, label: str) -> None:
    visualize(view)
    out = TMP_DIR / f"layout_{label}.html"
    shutil.copy(TMP_DIR / "layout_visualization.html", out)
    print(f"  visualization -> {out}")


def eval_mockdown(examples: list[dict]) -> tuple[float, float]:
    views = [View(**ex) for ex in examples]
    mk = Mockdown()
    mk.fit(views)
    rmsds = []
    accs = []
    for v in views:
        pred = mk.predict(width=v.width, height=v.height)
        rmsds.append(calculate_rmsd(pred, v))
        accs.append(calculate_accuracy(pred, v))
    return mean(rmsds), mean(accs)


def eval_conditional(examples: list[dict]) -> tuple[float, float]:
    views = [View(**ex) for ex in examples]
    cm = ConditionalMockdown()
    cm.fit(views)
    rmsds = []
    accs = []
    for v in views:
        pred = cm.predict(width=v.width, height=v.height)
        rmsds.append(calculate_rmsd(pred, v))
        accs.append(calculate_accuracy(pred, v))
    return mean(rmsds), mean(accs)


def main():
    scraped_files = sorted(DATA_DIR.glob("*_scraped.json"))
    if not scraped_files:
        print("No *_scraped.json files found.")
        return

    for path in scraped_files:
        slug = path.stem.replace("_scraped", "")
        data = json.loads(path.read_text())
        examples = data.get("examples", [])
        horiz = [ex for ex in examples if ex.get("_viewport", {}).get("category") != "mobile"]
        vert = [ex for ex in examples if ex.get("_viewport", {}).get("category") == "mobile"]

        print(f"\n=== {slug} ===")
        # Visualize first of each orientation (if present)
        if horiz:
            visualize_one(View(**horiz[0]), f"{slug}_horizontal")
        if vert:
            visualize_one(View(**vert[0]), f"{slug}_vertical")

        if horiz:
            rmsd_h, acc_h = eval_mockdown(horiz)
            print(f"Original Mockdown (horizontal): RMSD={rmsd_h:.4f}, ACC={acc_h:.4f}")
        else:
            print("Original Mockdown (horizontal): skipped (no examples)")

        if vert:
            rmsd_v, acc_v = eval_mockdown(vert)
            print(f"Original Mockdown (vertical):   RMSD={rmsd_v:.4f}, ACC={acc_v:.4f}")
        else:
            print("Original Mockdown (vertical): skipped (no examples)")

        if examples:
            rmsd_c, acc_c = eval_conditional(examples)
            print(f"Conditional Mockdown (all):     RMSD={rmsd_c:.4f}, ACC={acc_c:.4f}")
        else:
            print("Conditional Mockdown (all): skipped (no examples)")


if __name__ == "__main__":
    main()

