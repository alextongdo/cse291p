# Implementation Milestones

## M1: Scaffolding
- Create package skeleton and stage directories
- Add pyproject/requirements, minimal CI, and placeholder tests

## M2: Input + View Hierarchy
- Implement input schema/loader/formats
- Implement view types/builder/loader/ops
- Tests: loader validation, isomorphism, traversal

## M3: Constraint Grammar
- Port types/constraints/factory/axioms/validation
- Tests: repr, to_dict, substitution, invariants

## M4: Sketch Generation
- Port visibility and numpy instantiator
- Tests: template count and shapes on small examples

## M5: Bayesian Learning (bayes/)
- Port simple and noise-tolerant learning with configs
- Tests: candidate scoring and stability under noise

## M6: Hierarchical Decomposition + Max-SMT (hierarchical_decomp/)
- Extract HierarchicalPruner; wire BlackBoxPruner + z3 helpers
- Tests: satisfiable selection on toy hierarchies; bound propagation

## M7: Orchestration, CLI/Service, Docs
- Implement pipeline/run and run_timeout; CLI flags; optional service
- Docs: Pipeline.md, API.md, Paper-Notes.md
- E2E tests on bench examples and `inferui/onetwo`

