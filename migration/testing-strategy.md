# Testing Strategy

## Unit Tests by Stage
- Input: schema validation, format adapters, error cases
- View: builder invariants, isomorphism, traversal order
- Constraint: repr/to_dict, substitution, kind predicates
- Instantiation: visibility detection, template generation counts
- Learning: candidate scoring distribution, determinism with fixed seeds
- Global Inference: relevant_constraint filtering, bound propagation
- Max-SMT: satisfiable subsets, model valuation extraction

## End-to-End Tests
- Small goldens: 1–3 views layouts (bench and default formats)
- `tests/inferui/onetwo` parity with original outputs
- Noise robustness: inject debug noise and verify stability bands

## Test Utilities
- Builders for small view hierarchies
- Randomized generators with fixed RNG seeds
- Snapshot testing of constraint JSON (stable sorting)

## CI Recommendations
- Run `pytest -q` on PRs
- Lint/type-check critical modules (optional)
- Cache z3 wheels to speed up CI

