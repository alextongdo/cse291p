# Configuration & Options

## CLI Flags (proposed)
- `--input-format {default,bench}`
- `--numeric-type {N,R,Q,Z}`
- `--instantiation {numpy,prolog}`
- `--learning {simple,heuristic,noisetolerant}`
- `--global {hierarchical}`
- `--max-smt {z3}`
- `--pruning-bounds MIN_W MIN_H MAX_W MAX_H` (use `-` for unspecified)
- `--debug-noise STDEV`
- `--debug-visibilities` (skip learning/pruning)
- `--debug-instantiation` (return templates only)
- `--timeout SECONDS`
- `--num-examples N`

## PipelineOptions (dataclass)
- `input_format: str = 'default'`
- `numeric_type: str = 'N'`
- `instantiation_method: str = 'numpy'`
- `learning_method: str = 'noisetolerant'`
- `pruning_method: str = 'hierarchical'`
- `pruning_bounds: Tuple[Optional[float],Optional[float],Optional[float],Optional[float]]`
- `debug_noise: float = 0.0`
- `debug_visibilities: bool = False`
- `debug_instantiation: bool = False`
- `num_examples: Optional[int] = None`
- `timeout: Optional[int] = None`
- `unambig: bool = False`

## Numeric Type Mapping
- `N` → `sym.Number`
- `R` → `sym.Float`
- `Q` → `sym.Rational`
- `Z` → `sym.Integer`

## Learning Config Defaults
- `NoiseTolerantLearningConfig.sample_count = len(examples)`
- `NoiseTolerantLearningConfig.max_offset = max(max(ex.width, ex.height) for ex in examples) + 10`

## Bounds Object
- Convert tuple to dict: `{min_w, min_h, max_w, max_h}`
- Provide `ISizeBounds` type in `hierarchical_decomp/types.py`

