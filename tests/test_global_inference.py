import sympy as sym

from cse291p.pipeline.view.loader import ViewLoader
from cse291p.pipeline.sketch_generation.numpy import NumpyConstraintInstantiator
from cse291p.pipeline.bayes.simple import SimpleLearning, SimpleLearningConfig
from cse291p.pipeline.hierarchical_decomp.blackbox import BlackBoxPruner


def _examples():
    data = [{
        "name": "root",
        "rect": [0, 0, 100, 100],
        "children": [{"name": "child", "rect": [10, 10, 60, 60]}]
    }, {
        "name": "root",
        "rect": [0, 0, 120, 100],
        "children": [{"name": "child", "rect": [10, 10, 60, 60]}]
    }]
    loader = ViewLoader(number_type=sym.Number, input_format='default')
    return [loader.load_dict(d) for d in data]


def test_blackbox_pruner_runs():
    examples = _examples()
    inst = NumpyConstraintInstantiator(examples)
    templates = inst.instantiate()
    learner = SimpleLearning(templates=templates, samples=examples, config=SimpleLearningConfig())
    cand_lists = learner.learn()
    candidates = [c for lst in cand_lists for c in lst]
    bounds = {
        'min_w': sym.Rational(min(e.width for e in examples)),
        'min_h': sym.Rational(min(e.height for e in examples)),
        'max_w': sym.Rational(max(e.width for e in examples)),
        'max_h': sym.Rational(max(e.height for e in examples)),
    }
    pruner = BlackBoxPruner(examples, bounds, solve_unambig=False)
    kept, min_vals, max_vals = pruner(candidates)
    assert isinstance(kept, list)

