import sympy as sym

from cse291p.pipeline.view.loader import ViewLoader


def test_loader_default_format():
    data = {
        "examples": [
            {
                "name": "root",
                "rect": [0, 0, 100, 100],
                "children": [
                    {"name": "child", "rect": [10, 10, 60, 60]}
                ]
            }
        ]
    }
    loader = ViewLoader(number_type=sym.Number, input_format='default')
    view = loader.load_dict(data["examples"][0])
    assert view.name == "root"
    assert view.width == 100
    assert view.height == 100
    assert len(view.children) == 1


def test_loader_bench_format():
    data = {
        "train": [
            {
                "name": "root",
                "left": 0, "top": 0, "width": 100, "height": 100,
                "children": [
                    {"name": "child", "left": 10, "top": 10, "width": 50, "height": 50}
                ]
            }
        ]
    }
    loader = ViewLoader(number_type=sym.Number, input_format='bench')
    view = loader.load_dict(data["train"][0])
    assert view.left == 0
    assert view.top == 0
    assert view.right == 100
    assert view.bottom == 100

