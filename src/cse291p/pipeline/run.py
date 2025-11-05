"""Pipeline orchestrator - coordinates all stages of constraint synthesis.

Stages:
1) Input → View hierarchy
2) Sketch generation (templates)
3) Bayesian learning (parameters)
4) Global inference (hierarchical decomposition + Max-SMT)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type

import click
import sympy as sym

from cse291p.pipeline.view.loader import ViewLoader
from cse291p.pipeline.sketch_generation import get_prolog_instantiator_factory
from cse291p.pipeline.sketch_generation.numpy import NumpyConstraintInstantiator
from cse291p.pipeline.bayes.simple import SimpleLearning, SimpleLearningConfig, HeuristicLearning
from cse291p.pipeline.bayes.noisetolerant.learning import NoiseTolerantLearning
from cse291p.pipeline.bayes.noisetolerant.types import NoiseTolerantLearningConfig
from cse291p.pipeline.hierarchical_decomp.blackbox import BlackBoxPruner
from cse291p.pipeline.hierarchical_decomp.hierarchical import HierarchicalPruner

logger = logging.getLogger(__name__)


MockdownInput = Dict[str, Any]
MockdownOptions = Dict[str, Any]
MockdownResults = Dict[str, Any]


def synthesize(input_data: MockdownInput, options: MockdownOptions) -> MockdownResults:
    logger.info(f"Running with options: {options}")

    input_format = options.get('input_format', 'default')
    number_type: Type = {
        'N': sym.Number,
        'R': sym.Float,
        'Q': sym.Rational,
        'Z': sym.Integer
    }[options.get('numeric_type', 'N')]

    if input_format == 'default':
        examples_data = input_data["examples"]
    elif input_format == 'bench':
        examples_data = input_data["train"]
    else:
        raise ValueError("unknown input_format")

    # 1) Load examples → Views
    loader = ViewLoader(number_type=number_type, input_format=input_format, debug_noise=options.get('debug_noise', 0))
    examples = [loader.load_dict(ex) for ex in examples_data]

    # 2) Sketch generation
    inst_method = options.get('instantiation_method', 'numpy')
    if inst_method == 'numpy':
        instantiator = NumpyConstraintInstantiator(examples)
    elif inst_method == 'prolog':
        inst_factory = get_prolog_instantiator_factory()
        instantiator = inst_factory(examples)
    else:
        raise ValueError("unknown instantiation_method")
    templates = instantiator.instantiate()

    # 3) Learning
    learning_method = options.get('learning_method', 'noisetolerant')
    if learning_method == 'simple':
        cfg: Any = SimpleLearningConfig()
        learner = SimpleLearning(templates=templates, samples=examples, config=cfg)
    elif learning_method == 'heuristic':
        cfg = SimpleLearningConfig()
        learner = HeuristicLearning(templates=templates, samples=examples, config=cfg)
    elif learning_method == 'noisetolerant':
        max_offset = max((max(ex.width, ex.height) for ex in examples)) + 10
        cfg = NoiseTolerantLearningConfig(sample_count=len(examples), max_offset=max_offset)
        learner = NoiseTolerantLearning(templates=templates, samples=examples, config=cfg)
    else:
        raise ValueError("unknown learning_method")
    candidate_lists = learner.learn()
    candidates = [c for lst in candidate_lists for c in lst]

    # 4) Global inference. Use top-level bounds from examples.
    root = examples[0]
    min_w = min(e.width for e in examples)
    min_h = min(e.height for e in examples)
    max_w = max(e.width for e in examples)
    max_h = max(e.height for e in examples)
    bounds = {
        'min_w': sym.Rational(min_w),
        'min_h': sym.Rational(min_h),
        'max_w': sym.Rational(max_w),
        'max_h': sym.Rational(max_h),
    }

    # Support both BlackBoxPruner (baseline) and HierarchicalPruner
    pruning_method = options.get('pruning_method', 'baseline')
    if pruning_method == 'baseline':
        pruner = BlackBoxPruner(examples, bounds, options.get('unambig', False), targets=[root] + list(root.children))
    elif pruning_method == 'hierarchical':
        pruner = HierarchicalPruner(examples, bounds, options.get('unambig', False))
    else:
        raise ValueError(f"unknown pruning_method: {pruning_method}")
    
    pruned_constraints, min_vals, max_vals = pruner(candidates)

    result: MockdownResults = {
        'constraints': [cn.to_dict() for cn in pruned_constraints],
        'axioms': [],
        'valuations_min': {k: str(v) for k, v in (min_vals or {}).items()},
        'valuations_max': {k: str(v) for k, v in (max_vals or {}).items()},
    }

    return result


@click.command()
@click.option('--input-file', '-i', type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True,
              help='Path to JSON input. For default format, expects {"examples": [...]} with default records. For bench, {"train": [...]}')
@click.option('--input-format', type=click.Choice(['default', 'bench']), default='default')
@click.option('--numeric-type', type=click.Choice(['N', 'R', 'Q', 'Z']), default='N')
@click.option('--instantiation-method', type=click.Choice(['numpy', 'prolog']), default='numpy')
@click.option('--learning-method', type=click.Choice(['simple', 'heuristic', 'noisetolerant']), default='noisetolerant')
@click.option('--unambig/--no-unambig', default=False, help='Synthesize unambiguous layout (stronger).')
def main(input_file: Path, input_format: str, numeric_type: str, instantiation_method: str, learning_method: str, unambig: bool) -> None:
    """Run one pipeline synthesis from a JSON file and print JSON output."""
    with input_file.open('r') as fh:
        input_data = json.load(fh)
    options: MockdownOptions = {
        'input_format': input_format,
        'numeric_type': numeric_type,
        'instantiation_method': instantiation_method,
        'learning_method': learning_method,
        'unambig': unambig,
    }
    output = synthesize(input_data, options)
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()


