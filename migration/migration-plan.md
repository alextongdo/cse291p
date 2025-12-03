# CSE291P Complete Reimplementation Plan

## Overview

Restructure the mockdown codebase into a clear, pipeline-oriented architecture aligned with the paper's methodology:

1. JSON Input
2. View Hierarchy
3. Constraint Grammar and Representation
4. Local Inference: Generate Sketch
5. Local Inference: Bayesian Learning
6. Global Inference: Hierarchical Decomposition
7. Global Inference: Max-SMT Solve

## Target Directory Structure

```
/Users/xurui/Downloads/FA25/cse291p/
  pyproject.toml
  README.md
  requirements.txt
  uv.lock
  docs/
    Pipeline.md
    API.md
    Component-to-Code.md
    Paper-Notes.md
  src/
    cse291p/
      __init__.py
      cli.py
      app.py
      pipeline/
        __init__.py
        run.py

        input/
          __init__.py
          schema.py
          loader.py
          formats.py

        view/
          __init__.py
          types.py
          primitives.py
          builder.py
          loader.py
          ops.py

        constraint/
          __init__.py
          types.py
          constraint.py
          factory.py
          axioms.py
          validation.py

        instantiation/
          __init__.py
          types.py
          visibility.py
          numpy/
            __init__.py
            instantiator.py
          prolog/
            __init__.py
            instantiator.py
            logic.py
            logic.pl

        bayes/
          __init__.py
          types.py
          simple.py
          heuristic.py
          noisetolerant/
            __init__.py
            learning.py
            math.py
            util.py

        hierarchical_decomp/
          __init__.py
          types.py
          util.py
          conformance.py
          blackbox.py
          hierarchical.py
        integration/
          __init__.py
          z3.py
          kiwi.py

        output/
          __init__.py
          typing.py

      scraping/
        __init__.py
        scraper.py
  tests/
    __init__.py
    test_input_loader.py
    test_view.py
    test_constraint_types.py
    test_instantiation_numpy.py
    test_learning_noisetolerant.py
    test_global_inference.py
    inferui/
      __init__.py
      test_onetwo.py
```

## Goals

- Clear pipeline flow with explicit inputs/outputs
- Stable interfaces per stage with minimal coupling
- Unit-testable modules and end-to-end parity
- Directory names mirror the paper stages

## Dependencies

- sympy, numpy, pandas
- z3-solver
- pyswip (optional for prolog)
- click, starlette (optional), kiwisolver (optional)
- pydantic or jsonschema
- pytest

## Design Principles

1. Single responsibility per module
2. Explicit interfaces between stages
3. Immutable forward data flow
4. Configurable backends
5. Debuggable stages

