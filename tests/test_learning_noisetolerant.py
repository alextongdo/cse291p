import sympy as sym

from cse291p.pipeline.view.loader import ViewLoader
from cse291p.pipeline.sketch_generation.numpy import NumpyConstraintInstantiator
from cse291p.pipeline.bayes.noisetolerant.learning import NoiseTolerantLearning
from cse291p.pipeline.bayes.noisetolerant.types import NoiseTolerantLearningConfig


def _examples_many():
    data = [
        {"name": "root", "rect": [0, 0, 100, 100], "children": [{"name": "child", "rect": [10, 10, 60, 60]}]},
        {"name": "root", "rect": [0, 0, 120, 100], "children": [{"name": "child", "rect": [10, 10, 60, 60]}]},
        {"name": "root", "rect": [0, 0, 80,  100], "children": [{"name": "child", "rect": [10, 10, 60, 60]}]},
    ]
    loader = ViewLoader(number_type=sym.Number, input_format='default')
    return [loader.load_dict(d) for d in data]


def test_noisetolerant_learning_candidates():
    examples = _examples_many()
    inst = NumpyConstraintInstantiator(examples)
    templates = inst.instantiate()
    cfg = NoiseTolerantLearningConfig(sample_count=len(examples), max_offset=200)
    learner = NoiseTolerantLearning(templates=templates, samples=examples, config=cfg)
    cand_lists = learner.learn()
    # Some templates may be rejected; ensure structure is a list of lists
    assert isinstance(cand_lists, list)
    for lst in cand_lists:
        assert isinstance(lst, list)

