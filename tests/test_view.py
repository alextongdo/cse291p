import sympy as sym

from cse291p.pipeline.view.builder import ViewBuilder


def test_view_builder_sets_parent_children():
    root = ViewBuilder(name="root", rect=(0, 0, 100, 100), children=[
        ViewBuilder(name="child", rect=(10, 10, 60, 60))
    ])
    view = root.build(number_type=sym.Number)
    assert view.name == "root"
    assert len(view.children) == 1
    assert view.children[0].parent == view
    # Derived values
    assert view.width == 100
    assert view.height == 100

