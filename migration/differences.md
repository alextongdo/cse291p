# Differences from Original Mockdown Implementation

This document details all differences between the original `mockdown` codebase and the refactored `cse291p` implementation.

## Overview

The refactoring restructured the codebase to align with a clear pipeline-oriented architecture, making the synthesis stages explicit and easier to navigate. The core algorithms and logic remain unchanged, but the organization, naming, and some features have been modified.

---

## 1. Directory Structure Changes

### Major Reorganization

**Original (`mockdown/src/mockdown/`):**
```
mockdown/
├── model/              # View hierarchy and primitives
│   ├── view/
│   ├── primitives/
│   ├── anchor.py
│   ├── edge.py
│   └── types.py
├── instantiation/      # Sketch generation
├── learning/           # Bayesian learning
├── pruning/            # Global inference
├── constraint/
├── integration/
├── output/
└── scraping/
```

**Refactored (`cse291p/src/cse291p/pipeline/`):**
```
cse291p/
└── pipeline/
    ├── input/          # NEW: Explicit input handling
    ├── view/           # Renamed from model/
    ├── sketch_generation/  # Renamed from instantiation/
    ├── bayes/          # Renamed from learning/
    ├── hierarchical_decomp/  # Renamed from pruning/
    ├── constraint/
    ├── integration/
    ├── output/
    └── run.py          # Simplified orchestrator
```

### Key Changes:
- **`model/` → `view/`**: Renamed to reflect focus on view hierarchy representation
- **`instantiation/` → `sketch_generation/`**: More descriptive name aligned with paper terminology
- **`learning/` → `bayes/`**: Shorter, clearer name for Bayesian learning module
- **`pruning/` → `hierarchical_decomp/`**: Reflects both hierarchical decomposition and Max-SMT solving
- **New `input/` module**: Extracted input loading/validation from scattered locations

---

## 2. Module and File Changes

### 2.1 Input Handling (`pipeline/input/`)

**New module** - extracted from:
- `mockdown/model/view/loader.py` (format detection, rect conversion)
- `mockdown/cli.py` (JSON loading logic)
- `mockdown/run.py` (input_data parsing)

**New files:**
- `input/schema.py`: Pydantic models for input validation (`ViewDict`, `DefaultFormatInput`, `BenchFormatInput`)
- `input/formats.py`: Format conversion functions (`normalize_to_default_format`)
- `input/loader.py`: Unified loading API (`load_from_file`, `load_from_dict`)

**Removed:**
- Inline format detection in `ViewLoader.load_dict()` - now explicit format parameter

---

### 2.2 View Hierarchy (`pipeline/view/`)

**Renamed from `model/`** - consolidated structure:

| Original | New | Changes |
|----------|-----|---------|
| `model/view/view.py` | `view/view.py` | Same logic, cleaner imports |
| `model/view/builder.py` | `view/builder.py` | Unchanged |
| `model/view/loader.py` | `view/loader.py` | Simplified - delegates to `input/loader.py` |
| `model/view/types.py` | `view/types.py` | Merged with `model/types.py` |
| `model/types.py` | `view/types.py` | Merged into view module |
| `model/anchor.py` | `view/types.py` | Anchor classes merged into types |
| `model/edge.py` | `view/types.py` | Edge classes merged into types |
| `model/primitives/attribute.py` | `view/primitives.py` | Consolidated primitives |
| `model/primitives/geometry.py` | `view/primitives.py` | Consolidated primitives |
| `model/primitives/identifiers.py` | `view/primitives.py` | Consolidated primitives |
| - | `view/ops.py` | **NEW**: Utility functions for view operations (isomorphism, traversal) |

**Changes:**
- Consolidated `primitives/` subdirectory into single `primitives.py` file
- Merged `anchor.py` and `edge.py` into `types.py` for better cohesion
- Added `ops.py` for view-related utility functions extracted from `view.py`

---

### 2.3 Sketch Generation (`pipeline/sketch_generation/`)

**Renamed from `instantiation/`** - clearer terminology:

| Original | New | Changes |
|----------|-----|---------|
| `instantiation/` | `sketch_generation/` | Directory rename only |
| `instantiation/types.py` | `sketch_generation/types.py` | Unchanged |
| `instantiation/visibility.py` | `sketch_generation/visibility.py` | Unchanged |
| `instantiation/normalization.py` | `sketch_generation/normalization.py` | Unchanged |
| `instantiation/numpy/` | `sketch_generation/numpy/` | Unchanged |
| `instantiation/prolog/` | `sketch_generation/prolog/` | Unchanged |

**No functional changes** - pure rename for clarity.

---

### 2.4 Bayesian Learning (`pipeline/bayes/`)

**Renamed from `learning/`** - shorter, clearer name:

| Original | New | Changes |
|----------|-----|---------|
| `learning/` | `bayes/` | Directory rename only |
| `learning/types.py` | `bayes/types.py` | Unchanged |
| `learning/errors.py` | `bayes/errors.py` | Unchanged |
| `learning/util.py` | `bayes/util.py` | Unchanged |
| `learning/simple.py` | `bayes/simple.py` | Unchanged |
| `learning/noisetolerant/` | `bayes/noisetolerant/` | Unchanged |

**No functional changes** - pure rename.

---

### 2.5 Global Inference (`pipeline/hierarchical_decomp/`)

**Renamed from `pruning/`** - reflects both decomposition and Max-SMT:

| Original | New | Changes |
|----------|-----|---------|
| `pruning/` | `hierarchical_decomp/` | Directory rename |
| `pruning/types.py` | `hierarchical_decomp/types.py` | **Removed** `MarginPruner`, `DynamicPruner` (see below) |
| `pruning/util.py` | `hierarchical_decomp/util.py` | Unchanged |
| `pruning/conformance.py` | `hierarchical_decomp/conformance.py` | Simplified implementation |
| `pruning/blackbox.py` | `hierarchical_decomp/blackbox.py` | **Split**: Only `BlackBoxPruner` remains |
| `pruning/blackbox.py` | `hierarchical_decomp/hierarchical.py` | **NEW**: Extracted `HierarchicalPruner` |

**Major Changes:**
- **Split `blackbox.py`**: Original file contained both `BlackBoxPruner` and `HierarchicalPruner`. Now separated:
  - `blackbox.py`: Contains only `BlackBoxPruner` (Max-SMT solving)
  - `hierarchical.py`: Contains only `HierarchicalPruner` (hierarchical decomposition)
- **Removed classes**: `MarginPruner` and `DynamicPruner` - these were commented out in original `run.py` and not actively used
- **Removed `validation.py`**: Empty placeholder file in original codebase

---

### 2.6 Constraint Grammar (`pipeline/constraint/`)

**Minimal changes** - mostly preserved:

| Original | New | Changes |
|----------|-----|---------|
| `constraint/types.py` | `constraint/types.py` | Unchanged |
| `constraint/constraint.py` | `constraint/constraint.py` | Unchanged |
| `constraint/factory.py` | `constraint/factory.py` | Unchanged |
| `constraint/axioms.py` | `constraint/axioms.py` | Unchanged |
| `constraint/validation.py` | - | **REMOVED**: Empty placeholder file |

---

### 2.7 Integration (`pipeline/integration/`)

**No changes** - preserved as-is:
- `integration/z3.py`: Unchanged
- `integration/kiwi.py`: Unchanged

---

### 2.8 Output (`pipeline/output/`)

**No changes** - preserved as-is:
- `output/typing.py`: Unchanged

---

### 2.9 Orchestration (`pipeline/run.py`)

**Major simplification** - streamlined from original:

| Original (`mockdown/run.py`) | New (`cse291p/pipeline/run.py`) | Changes |
|------------------------------|----------------------------------|---------|
| `run_timeout()` | - | **REMOVED**: Timeout wrapper (can be added if needed) |
| `run()` | `synthesize()` | Renamed, simplified signature |
| `MockdownInput` TypedDict | `Dict[str, Any]` | Simplified typing |
| `MockdownOptions` TypedDict | `Dict[str, Any]` | Simplified typing |
| `MockdownResults` TypedDict | `Dict[str, Any]` | Simplified typing |
| Profile support | - | **REMOVED**: `cProfile` integration (can be re-added) |
| `num_examples` option | - | **REMOVED**: Subset examples (can be re-added) |
| `debug_visibilities` | - | **REMOVED**: Debug flag (can be re-added) |
| `debug_instantiation` | - | **REMOVED**: Debug flag (can be re-added) |
| `include_axioms` | - | **REMOVED**: Axiom generation (can be re-added) |
| `pruning_method` factory | - | **REMOVED**: Only `BlackBoxPruner` supported now |
| `pruning_bounds` tuple | `bounds` dict | Simplified bounds format |
| `result_queue` multiprocessing | - | **REMOVED**: Multiprocessing support (can be re-added) |
| - | `main()` CLI function | **NEW**: Click-based CLI entrypoint |

**New CLI:**
- Added Click-based command-line interface directly in `run.py`
- Simplified options compared to original `cli.py`

---

### 2.10 CLI (`cli.py`)

**Original (`mockdown/cli.py`):**
- Full-featured Click CLI with multiple commands:
  - `run`: Main synthesis command with extensive options
  - `scrape`: Web scraping functionality
  - `display`: HTML visualization
  - `serve`: Web server for API

**New (`cse291p/cli.py`):**
- **NOT IMPLEMENTED YET** - CLI functionality moved to `pipeline/run.py::main()`
- Original `cli.py` preserved as placeholder for future full CLI

**Removed features:**
- `scrape` command: Web scraping functionality not ported
- `display` command: HTML visualization not ported
- `serve` command: Web server not ported

---

### 2.11 App/Server (`app.py`)

**Original (`mockdown/app.py`):**
- Starlette-based web server with `/api/synthesize` endpoint
- CORS middleware
- Static file serving

**New (`cse291p/app.py`):**
- **NOT IMPLEMENTED YET** - preserved as placeholder
- Web server functionality not ported in initial refactoring

---

### 2.12 Display (`display/`)

**Original (`mockdown/display/`):**
- Jinja2 templates for HTML visualization of **input examples** (not synthesis results)
- JavaScript files for interactive display
- Used by `cli.py display` command
- Visualizes the training examples as colored overlay boxes showing view hierarchies
- Can optionally show the original webpage in an iframe if scraped

**Purpose**: Debugging/inspection tool to visually verify input examples before synthesis

**New:**
- **NOT PORTED** - display functionality removed from refactored codebase

---

### Output Examination in Original Mockdown

**How synthesis output was examined:**

1. **JSON output** (via CLI): Constraints serialized via `to_dict()` to JSON file
   - Fields: `y`, `op`, `b`, `a`, `x`, `kind`, `strength`
   - Example: `{'y': 'root.width', 'op': '=', 'b': '100', ...}`

2. **Logging output**: Human-readable constraint strings via `__repr__()`
   - Example: `"root.width = 100"` or `"child.left = root.left + 10"`
   - Logged as "KEPT:" and "PRUNED:" lists

3. **String representation**: Constraints have `__repr__()` and `short_str()` utilities
   - Readable format for debugging

4. **Debug files**: Z3 SMT2 solver files written when debugging (e.g., `"unsat-*.smt2"`)

5. **No visual viewer**: No graphical constraint visualization tool - entirely text-based

**Note**: The `display/` module was only for visualizing **input examples**, not synthesis results.

---

### Reading/Parsing Synthesis Output

**Output format structure:**

The synthesis output is a JSON object with the following structure:

```json
{
  "constraints": [
    {
      "y": "root.width",
      "op": "=",
      "b": "100",
      "strength": "required",
      "kind": "size_constant"
    },
    {
      "y": "child.left",
      "op": "=",
      "a": "1",
      "x": "root.left",
      "b": "10",
      "strength": "required",
      "kind": "pos_ltrb_offset"
    }
  ],
  "axioms": [],
  "valuations_min": {
    "root.width": "100",
    "root.height": "100",
    "child.left": "10"
  },
  "valuations_max": {
    "root.width": "100",
    "root.height": "100",
    "child.left": "10"
  }
}
```

**Field descriptions:**

1. **`constraints`** (array): List of synthesized constraints
   - Each constraint is a dictionary with fields:
     - **`y`** (string): Target anchor ID (e.g., `"root.width"`, `"child.left"`)
     - **`op`** (string): Operator - `"="`, `"≤"`, or `"≥"`
     - **`b`** (string): Constant value (always present, may be `"0"`)
     - **`a`** (string, optional): Multiplier for linear constraints (e.g., `"1"`, `"2"`, `"1/2"`)
     - **`x`** (string, optional): Dependent anchor ID for linear constraints (e.g., `"root.width"`, `"child.left"`)
     - **`strength`** (string): Priority level - `"required"`, `"strong"`, `"weak"`, etc.
     - **`kind`** (string): Constraint type - `"size_constant"`, `"pos_ltrb_offset"`, `"size_aspect_ratio"`, etc.

2. **`axioms`** (array): Layout axioms (optional, only if `include_axioms=True` in original)
   - List of axiom strings describing layout relationships
   - **Note**: Not currently generated in refactored version

3. **`valuations_min`** (dict, optional): **NEW in refactored version**
   - Minimum anchor valuations from solver model
   - See "Additional fields" section below

4. **`valuations_max`** (dict, optional): **NEW in refactored version**
   - Maximum anchor valuations from solver model
   - See "Additional fields" section below

**Constraint types:**

- **Constant constraint** (`y = b`): Only `y`, `op`, `b` fields present
  - Example: `{"y": "root.width", "op": "=", "b": "100", ...}`
  
- **Linear constraint** (`y = a * x + b`): All fields including `a` and `x` present
  - Example: `{"y": "child.left", "op": "=", "a": "1", "x": "root.left", "b": "10", ...}`

**Reading the output:**

1. **From JSON file** (CLI output):
   ```python
   import json
   with open('output.json', 'r') as f:
       result = json.load(f)
   constraints = result['constraints']
   ```

2. **From Python API** (returned dict):
   ```python
   from mockdown.run import run
   result = run(input_data, options)
   constraints = result['constraints']
   ```

3. **Parsing constraint strings** (from logging):
   - Constraints use `__repr__()` format: `"root.width = 100"` or `"child.left = root.left + 10"`
   - Can parse manually or use constraint factory to reconstruct

4. **Validating constraints**:
   - Use `ConstraintFactory.create()` with constraint kind and fields
   - Or parse anchor IDs and reconstruct constraint objects

**Anchor ID format:**
- Format: `"{view_name}.{attribute}"`
- Examples: `"root.width"`, `"child.left"`, `"root.center_x"`, `"child.top"`

**Operator values:**
- `"="`: Equality constraint
- `"≤"`: Less than or equal
- `"≥"`: Greater than or equal

**Additional fields in refactored version:**

The refactored `cse291p` implementation adds optional fields for model valuations:

- **`valuations_min`** (dict, optional): Minimum anchor valuations from solver model
  - Keys: anchor IDs (e.g., `"root.width"`)
  - Values: string representations of minimum values
  - Example: `{"root.width": "100", "child.left": "10"}`

- **`valuations_max`** (dict, optional): Maximum anchor valuations from solver model
  - Keys: anchor IDs (e.g., `"root.width"`)
  - Values: string representations of maximum values
  - Example: `{"root.width": "200", "child.left": "20"}`

These fields are populated when the solver extracts model valuations (e.g., from `BlackBoxPruner`). They represent the min/max bounds for each anchor variable in the solved constraint system.

**Note**: The refactored `cse291p` implementation preserves the same output format for compatibility, with these additional optional fields.

---

### Constraint Evaluation in Original Mockdown

**How synthesized constraints were evaluated:**

The original codebase evaluated constraints using the **Kiwi constraint solver** to validate that constraints are satisfiable and can produce a concrete layout.

**Primary evaluation function: `evaluate_constraints()`**

Located in `mockdown/integration/kiwi.py`, this function:

1. **Inputs:**
   - `view`: View hierarchy (IView)
   - `top_rect`: Top-level rectangle bounds (Rect with left, top, right, bottom)
   - `constraints`: List of synthesized constraints (List[IConstraint])
   - `strength`: Constraint strength (default: 'strong')

2. **Process:**
   - Creates a Kiwi solver instance
   - Adds layout axioms (width = right - left, height = bottom - top, centers, non-negativity)
   - Adds synthesized constraints to the solver
   - Fixes top-level view bounds (left, top, right, bottom) to the provided rectangle
   - Solves the constraint system

3. **Output:**
   - Returns a new view hierarchy (IView[sym.Float]) with computed positions/sizes
   - If constraints are unsatisfiable, Kiwi solver will raise an exception

**Usage in validation:**

The `HierarchicalPruner` class has a `validate_output_constrs()` method that:

1. **Cross-validates with Z3**: First validates against `BlackBoxPruner` baseline (Z3 solver)
2. **Validates with Kiwi**: Then calls `evaluate_constraints()` to ensure Kiwi solver can also satisfy the constraints
3. **Raises exception**: If constraints are unsatisfiable in either solver

**Example usage:**

```python
from mockdown.integration import evaluate_constraints
from mockdown.model.primitives import Rect

# Evaluate constraints on a view hierarchy
top_rect = Rect(left=0, top=0, right=100, bottom=100)
solved_view = evaluate_constraints(view_hierarchy, top_rect, synthesized_constraints)

# The solved_view contains computed positions/sizes for all views
# If constraints are unsatisfiable, an exception is raised
```

**Evaluation approach:**

1. **Satisfiability check**: Validates that constraints are satisfiable (not contradictory)
2. **Layout generation**: Produces a concrete layout showing what the constraints would produce
3. **Solver validation**: Uses both Z3 (for Max-SMT solving) and Kiwi (for layout validation) to ensure consistency

**Note**: The refactored `cse291p` implementation already includes `evaluate_constraints()` in `pipeline/integration/kiwi.py` - it's fully ported and functional.

---

### 2.13 Scraping (`scraping/`)

**Original (`mockdown/scraping/`):**
- Web scraping functionality
- Used by `cli.py scrape` command

**New (`cse291p/scraping/`):**
- **PLACEHOLDER ONLY** - preserved structure but not implemented

---

### 2.14 Resources (`resources/`)

**Original (`mockdown/resources/`):**
- Example JSON files for testing

**New:**
- **NOT PORTED** - resources not included in refactored codebase

---

## 3. Removed Classes and Features

### 3.1 Removed Pruning Methods

**`MarginPruner`** and **`DynamicPruner`**:
- Located in `mockdown/pruning/types.py`
- Were commented out in original `run.py` (lines 135-136)
- Not actively used in original codebase
- **Removed** from refactored implementation

### 3.2 Removed Empty/Placeholder Files

- `constraint/validation.py`: Empty placeholder in original
- Files that were placeholders with no actual implementation

### 3.3 Removed Features from `run.py`

- **Timeout wrapper**: `run_timeout()` with multiprocessing
- **Profiling**: `cProfile` integration
- **Debug flags**: `debug_visibilities`, `debug_instantiation`
- **Axiom generation**: `include_axioms` option
- **Example subsetting**: `num_examples` option
- **Pruning method factory**: Only `BlackBoxPruner` supported now

---

## 4. API Changes

### 4.1 View Loading

**Original:**
```python
from mockdown.model import ViewLoader
loader = ViewLoader(number_type=sym.Number, input_format='default', debug_noise=0)
view = loader.load_dict(ex_data)
```

**New:**
```python
from cse291p.pipeline.view.loader import ViewLoader
loader = ViewLoader(number_type=sym.Number, input_format='default', debug_noise=0)
view = loader.load_dict(ex_data)
```

**Change**: Import path only - same API.

---

### 4.2 Constraint Instantiation

**Original:**
```python
from mockdown.instantiation import NumpyConstraintInstantiator
inst = NumpyConstraintInstantiator(examples)
```

**New:**
```python
from cse291p.pipeline.sketch_generation.numpy import NumpyConstraintInstantiator
inst = NumpyConstraintInstantiator(examples)
```

**Change**: Import path only - same API.

---

### 4.3 Learning

**Original:**
```python
from mockdown.learning.simple import SimpleLearning
learner = SimpleLearning(templates=templates, samples=examples, config=cfg)
```

**New:**
```python
from cse291p.pipeline.bayes.simple import SimpleLearning
learner = SimpleLearning(templates=templates, samples=examples, config=cfg)
```

**Change**: Import path only - same API.

---

### 4.4 Pruning

**Original:**
```python
from mockdown.pruning import BlackBoxPruner, HierarchicalPruner
pruner = BlackBoxPruner(examples, bounds, unambig)
```

**New:**
```python
from cse291p.pipeline.hierarchical_decomp.blackbox import BlackBoxPruner
from cse291p.pipeline.hierarchical_decomp.hierarchical import HierarchicalPruner
pruner = BlackBoxPruner(examples, bounds, solve_unambig=False, targets=[...])
```

**Changes:**
- Import paths updated
- `BlackBoxPruner.__init__()` now requires `targets` parameter explicitly
- `unambig` renamed to `solve_unambig` for clarity

---

### 4.5 Main Orchestration

**Original:**
```python
from mockdown.run import run_timeout
result = run_timeout(input_data, options, timeout=60)
```

**New:**
```python
from cse291p.pipeline.run import synthesize
result = synthesize(input_data, options)
```

**Changes:**
- Function renamed from `run()`/`run_timeout()` to `synthesize()`
- No timeout support (can be added via wrapper if needed)
- Simplified return type (same structure, but not TypedDict)

---

## 5. Type System Changes

### 5.1 TypedDict Simplification

**Original:**
```python
class MockdownInput(TypedDict):
    examples: List[Dict[str, Any]]
    options: MockdownOptions

class MockdownOptions(TypedDict, total=False):
    input_format: Literal['default', 'bench']
    # ... many fields
```

**New:**
```python
MockdownInput = Dict[str, Any]
MockdownOptions = Dict[str, Any]
```

**Change**: Simplified to plain dictionaries for flexibility. Same runtime behavior, less strict typing.

---

## 6. Code Quality Improvements

### 6.1 Imports

- **Standardized `sympy` imports**: All use `import sympy as sym` consistently
- **Cleaner module structure**: Fewer circular dependencies
- **Explicit exports**: Better `__init__.py` files with clear public APIs

### 6.2 Error Handling

- **Preserved**: All original error handling logic maintained
- **No changes**: Exception types and error messages unchanged

### 6.3 Documentation

- **Added**: `Reimplements` comments in each file referencing original code
- **Improved**: Clearer module docstrings explaining pipeline stage
- **Preserved**: Original inline comments and docstrings

---

## 7. Testing Changes

### 7.1 Test Structure

**Original (`mockdown/tests/`):**
- `test_builder.py`
- `test_loader.py`
- `inferui/test_onetwo.py`
- `learning/` (test directory)
- `model/test_view.py`

**New (`cse291p/tests/`):**
- `test_input_loader.py` - **NEW**: Input loading tests
- `test_view.py` - View hierarchy tests
- `test_constraint_types.py` - Constraint tests
- `test_instantiation_numpy.py` - Sketch generation tests
- `test_learning_noisetolerant.py` - Bayesian learning tests
- `test_global_inference.py` - Global inference tests
- `test_sat_solver.py` - **NEW**: Z3 solver tests
- `test_e2e_pipeline.py` - **NEW**: End-to-end pipeline test

**Changes:**
- More comprehensive test coverage
- New end-to-end test
- Tests organized by pipeline stage

---

## 8. Dependencies

### 8.1 Unchanged Dependencies

- `sympy`, `numpy`, `pandas`, `scipy`, `statsmodels` - Same versions
- `z3-solver` - Same
- `kiwisolver` - Same
- `intervaltree` - Same
- `more-itertools` - Same

### 8.2 New Dependencies

- `pydantic` - For input schema validation (was implicit before)
- `click` - For CLI (was in original, now explicitly required)

### 8.3 Removed Dependencies

- `starlette` - Web server not ported (optional in original)
- `uvicorn` - Web server not ported (optional in original)
- `jinja2` - Display functionality not ported (optional in original)
- `pyswip` - Still optional for Prolog backend

---

## 9. Summary of Changes

### What Changed:
1. **Directory structure**: Reorganized to match pipeline stages
2. **Naming**: `instantiation` → `sketch_generation`, `learning` → `bayes`, `pruning` → `hierarchical_decomp`
3. **Module consolidation**: Merged related files (primitives, anchor/edge)
4. **Feature removal**: Removed unused pruning methods, debug features, web server
5. **Simplified orchestration**: Streamlined `run.py` to essential functionality
6. **New input module**: Explicit input handling and validation

### What Stayed the Same:
1. **Core algorithms**: All constraint synthesis logic unchanged
2. **Data structures**: View hierarchy, constraints, anchors, edges - all preserved
3. **Solver integration**: Z3 and Kiwi integration unchanged
4. **Mathematical models**: Bayesian learning, statistical inference - unchanged
5. **API compatibility**: Function signatures and behavior preserved (except removed features)

### Migration Path:
- Import paths updated (e.g., `mockdown.model` → `cse291p.pipeline.view`)
- Function names mostly preserved (`run()` → `synthesize()` is main change)
- Options dictionary format simplified but compatible
- Return value structure unchanged

---

## 10. Future Work

The following features from the original were not ported but could be re-added:
- Web server (`app.py`, Starlette)
- Web scraping (`scraping/scraper.py`)
- HTML visualization (`display/`)
- Timeout wrapper with multiprocessing
- Profiling support
- Debug flags for visibilities/instantiation
- Axiom generation
- Multiple pruning methods (if needed)
- Example subsetting option

