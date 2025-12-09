import json
from pathlib import Path

from src.main import Mockdown
from src.types import View
from src.visualize import visualize


def load_json(filename: str):
    path = Path(__file__).parent / filename
    with open(path) as f:
        return json.load(f)

data = load_json("data/hn.json")
examples = data["train"]

views = [View(**example) for example in examples]
mockdown = Mockdown()
mockdown.fit(views)
rects = mockdown.predict(width=views[0].width, height=views[0].height)
visualize(rects, root_name=views[0].name)
