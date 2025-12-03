# Stage-by-Stage Module Mapping

This document maps existing mockdown modules to the proposed `cse291p` pipeline.

## 1) JSON Input → `pipeline/input/`
- mockdown: `model/view/loader.py` (dict → view), `cli.py` (format handling)
- new: `input/loader.py` (load_from_file/load_from_dict), `input/formats.py` (default/bench), `input/schema.py` (validation)

## 2) View Hierarchy → `pipeline/view/`
- mockdown: `model/view/view.py`, `model/view/builder.py`, `model/types.py`, `model/primitives/*`, `model/view/loader.py`
- new: `view/types.py`, `view/builder.py`, `view/primitives.py`, `view/loader.py`, `view/ops.py`

## 3) Constraint Grammar → `pipeline/constraint/`
- mockdown: `constraint/types.py`, `constraint/constraint.py`, `constraint/factory.py`, `constraint/axioms.py`, `constraint/validation.py`
- new: same filenames and APIs for minimal friction

## 4) Local Inference: Generate Sketch → `pipeline/instantiation/`
- mockdown: `instantiation/visibility.py`, `instantiation/numpy/instantiator.py`, `instantiation/prolog/*`
- new: `instantiation/types.py` (IConstraintInstantiator), `instantiation/visibility.py`, and backend dirs unchanged

## 5) Local Inference: Bayesian Learning → `pipeline/bayes/`
- mockdown: `learning/simple.py`, `learning/noisetolerant/*`, `learning/types.py`
- new: same structure; configs are explicit (e.g., `NoiseTolerantLearningConfig`)

## 6) Global Inference: Hierarchical Decomposition → `pipeline/hierarchical_decomp/hierarchical.py`
- mockdown: `pruning/blackbox.py` (contains `HierarchicalPruner`)
- new: extract `HierarchicalPruner` into dedicated `hierarchical.py`

## 7) Global Inference: Max-SMT Solve → `pipeline/hierarchical_decomp/blackbox.py` + `pipeline/integration/z3.py`
- mockdown: `pruning/blackbox.py`, `integration/z3.py`
- new: preserve Optimize loop and `extract_model_valuations`, keep clean interface returning (constraints, min, max)

## Orchestration → `pipeline/run.py`
- mockdown: `run.py`
- new: name stages explicitly; keep `run_timeout` wrapper for CLI/server

