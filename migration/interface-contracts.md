# Interface Contracts by Stage

Define stable, minimal APIs between stages to enable testing and swapping implementations.

## Common Types
- `IView[NT]`, `IAnchor`, `IEdge`, `Rect`, `ViewName`
- `IConstraint`, `ConstraintKind`, `Priority`
- `ConstraintCandidate { constraint: IConstraint, score: float }`

## Stage 1: Input
- `load_from_file(path: str, format: Literal['default','bench']) -> List[dict]`
- `load_from_dict(data: dict, format: Literal['default','bench']) -> List[dict]`
- Validation: raises on schema violation

## Stage 2: View Hierarchy
- `build_view(example_dict: dict, number_type) -> IView`
- `is_isomorphic(a: IView, b: IView, include_names: bool = True) -> bool`
- Traversals: `iter(view) -> Iterator[IView]`

## Stage 3: Constraint Grammar
- `LinearConstraint(kind, y_id, x_id, a=1, b=0, op, priority)`
- `ConstantConstraint(kind, y_id, b, op, priority)`
- `Factory.make(kind, y_id, x_id=None) -> IConstraint`
- `constraint.to_dict() -> dict`

## Stage 4: Sketch Generation (Instantiation)
- Protocol `IConstraintInstantiator`:
- `__init__(examples: List[IView])`
- `instantiate() -> List[IConstraint]`  (templates, sample_count=0)
- Optional: `detect_visibilities() -> Any`

## Stage 5: Bayesian Learning → `pipeline/bayes/`
- Protocol `IConstraintLearning`:
- `__init__(samples: List[IView], templates: List[IConstraint], config: Any)`
- `learn() -> Iterable[List[ConstraintCandidate]]`
- Config examples:
- `NoiseTolerantLearningConfig(sample_count: int, max_offset: int)`

## Stage 6: Hierarchical Decomposition → `pipeline/hierarchical_decomp/`
- `HierarchicalPruner(examples: List[IView], bounds: dict, solve_unambig: bool)`
- Methods:
- `__call__(candidates: List[ConstraintCandidate]) -> Tuple[List[IConstraint], Dict[str, Fraction], Dict[str, Fraction]]`
- Internals: `relevant_constraint(focus: IView, c: IConstraint) -> bool`

## Stage 7: Max-SMT Solve → `pipeline/hierarchical_decomp/` + `pipeline/integration/`
- `BlackBoxPruner(examples: List[IView], bounds: dict, solve_unambig: bool, targets: List[IView])`
- `__call__(candidates: List[ConstraintCandidate]) -> Tuple[List[IConstraint], Dict[str, Fraction], Dict[str, Fraction]]`
- Z3 helpers:
- `extract_model_valuations(model, idx, names) -> Dict[str, Rational]`
- `load_view_from_model(model, idx, skeleton: IView) -> IView`

## Orchestration
- `synthesize(input_data: dict, options: dict) -> dict` (constraints JSON; optional axioms)
- Timeout wrapper: `run_timeout(input_data, options, timeout) -> Optional[dict]`

