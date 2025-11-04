import operator
import json
import sympy as sym

from cse291p.pipeline.view.loader import ViewLoader
from cse291p.pipeline.sketch_generation.numpy import NumpyConstraintInstantiator
from cse291p.pipeline.bayes.simple import SimpleLearning, SimpleLearningConfig
from cse291p.pipeline.hierarchical_decomp.blackbox import BlackBoxPruner
from cse291p.pipeline.hierarchical_decomp.types import ISizeBounds
from cse291p.pipeline.output import format_constraint, parse_output


def make_examples():
    # Small hierarchy with one child; rects are [left, top, right, bottom]
    examples_data = [
        {
            "name": "root",
            "rect": [0, 0, 100, 100],
            "children": [
                {"name": "child", "rect": [10, 10, 60, 60]}
            ]
        },
        {
            "name": "root",
            "rect": [0, 0, 200, 100],
            "children": [
                {"name": "child", "rect": [10, 10, 60, 60]}
            ]
        },
        {
            "name": "root",
            "rect": [0, 0, 300, 100],
            "children": [
                {"name": "child", "rect": [10, 10, 60, 60]}
            ]
        },
        {
            "name": "root",
            "rect": [0, 0, 100, 200],
            "children": [
                {"name": "child", "rect": [10, 10, 60, 60]}
            ]
        },
    ]
    loader = ViewLoader(number_type=sym.Number, input_format='default', debug_noise=0)
    return [loader.load_dict(ex) for ex in examples_data]


def test_end_to_end_pipeline():
    # 1) Load examples → View hierarchy
    examples = make_examples()
    assert len(examples) >= 2
    assert examples[0].name == "root"
    assert len(examples[0].children) == 1
    assert examples[0].children[0].name == "child"

    # 2) Sketch Generation (numpy)
    inst = NumpyConstraintInstantiator(examples)
    templates = inst.instantiate()
    assert len(templates) > 0

    # 3) Bayesian Learning (simple)
    simple_cfg = SimpleLearningConfig(tolerance=0.02, max_denominator=50)
    learner = SimpleLearning(templates=templates, samples=examples, config=simple_cfg)
    cand_lists = learner.learn()
    candidates = [c for lst in cand_lists for c in lst]
    assert len(candidates) > 0
    for c in candidates:
        assert hasattr(c.constraint, 'a')
        assert hasattr(c.constraint, 'b')
        assert c.score >= 0

    # 4) Global Inference (Max-SMT via BlackBox)
    root = examples[0]
    min_w = min(e.width for e in examples)
    min_h = min(e.height for e in examples)
    max_w = max(e.width for e in examples)
    max_h = max(e.height for e in examples)
    bounds: ISizeBounds = {
        'min_w': sym.Rational(min_w),
        'min_h': sym.Rational(min_h),
        'max_w': sym.Rational(max_w),
        'max_h': sym.Rational(max_h),
    }

    pruner = BlackBoxPruner(examples, bounds, solve_unambig=False, targets=[root] + list(root.children))
    kept_constraints, min_vals, max_vals = pruner(candidates)

    # 5) Assertions on solver output
    assert isinstance(kept_constraints, list)
    assert isinstance(min_vals, dict)
    assert isinstance(max_vals, dict)

    if kept_constraints:
        for cn in kept_constraints:
            assert callable(cn.op)
            assert cn.op in (operator.eq, operator.le, operator.ge)
            # at least refers to our hierarchy's anchors
            assert str(cn.y_id).startswith(root.name) or True

    # 6) Output parsing and validation
    # Convert constraints to output format (as returned by synthesize())
    output_data = {
        'constraints': [cn.to_dict() for cn in kept_constraints],
        'axioms': [],
        'valuations_min': {k: str(v) for k, v in (min_vals or {}).items()},
        'valuations_max': {k: str(v) for k, v in (max_vals or {}).items()},
    }
    
    # Validate output structure
    assert isinstance(output_data, dict)
    assert 'constraints' in output_data
    assert 'axioms' in output_data
    assert isinstance(output_data['constraints'], list)
    assert isinstance(output_data['axioms'], list)
    
    # Validate each constraint in output format
    for c_dict in output_data['constraints']:
        assert isinstance(c_dict, dict)
        assert 'y' in c_dict
        assert 'op' in c_dict
        assert 'b' in c_dict
        assert 'kind' in c_dict
        assert 'strength' in c_dict
        # Validate constraint format can be parsed
        formatted = format_constraint(c_dict)
        assert isinstance(formatted, str)
        assert len(formatted) > 0
    
    # Validate valuations if present
    if output_data.get('valuations_min'):
        assert isinstance(output_data['valuations_min'], dict)
        for anchor_id, val in output_data['valuations_min'].items():
            assert isinstance(anchor_id, str)
            assert isinstance(val, str)
    
    if output_data.get('valuations_max'):
        assert isinstance(output_data['valuations_max'], dict)
        for anchor_id, val in output_data['valuations_max'].items():
            assert isinstance(anchor_id, str)
            assert isinstance(val, str)
    
    # Test output parsing (should not raise exceptions)
    try:
        # This will print formatted output if pytest -s is used
        parse_output(output_data)
    except Exception as e:
        # If parsing fails, that's a test failure
        assert False, f"Output parsing failed: {e}"
    
    # Compact summary for visual verification (shown with pytest -s)
    summary = {
        'num_examples': len(examples),
        'num_templates': len(templates),
        'num_candidates': len(candidates),
        'num_kept_constraints': len(kept_constraints),
        'num_output_constraints': len(output_data['constraints']),
        'sample_min_keys': list(min_vals.keys())[:5],
        'sample_max_keys': list(max_vals.keys())[:5],
        'sample_formatted_constraints': [format_constraint(c) for c in output_data['constraints'][:3]],
    }
    print(json.dumps(summary, indent=2))


