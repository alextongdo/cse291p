import sympy as sym

from cse291p.pipeline.view.loader import ViewLoader
from cse291p.pipeline.sketch_generation.numpy import NumpyConstraintInstantiator
from cse291p.pipeline.constraint.types import ConstraintKind


def _examples():
    data = [{
        "name": "root",
        "rect": [0, 0, 100, 100],
        "children": [{"name": "child", "rect": [10, 10, 60, 60]}]
    }]
    loader = ViewLoader(number_type=sym.Number, input_format='default')
    return [loader.load_dict(d) for d in data]


def test_numpy_instantiator_produces_templates():
    examples = _examples()
    inst = NumpyConstraintInstantiator(examples)
    templates = inst.instantiate()
    assert len(templates) > 0
    kinds = {t.kind for t in templates}
    # Should include at least position offsets or size constraints
    assert ConstraintKind.SIZE_CONSTANT in kinds or ConstraintKind.POS_LTRB_OFFSET in kinds

