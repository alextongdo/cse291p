# Mockdown Codebase Documentation

## Overview

Mockdown is a Python implementation of the constraint-based layout synthesis algorithm described in the Mockdown paper. It takes hierarchical layout examples (JSON representations of UI layouts at different screen sizes) and synthesizes generalizable layout constraints of the form `y = a·x + b`.

The codebase is structured in a modular fashion following the paper's pipeline:
1. **Input Loading** - Parse JSON layout examples
2. **Local Inference (Instantiation)** - Generate candidate constraint templates
3. **Parameter Learning** - Infer constraint parameters using Bayesian regression
4. **Global Inference (Pruning)** - Select maximal satisfiable constraint subset using MaxSMT

## Project Structure

```
mockdown/
├── src/mockdown/           # Main source code
│   ├── model/              # Core data structures (Views, Anchors, Constraints)
│   ├── constraint/         # Constraint types and representations
│   ├── instantiation/      # Local inference - template generation
│   ├── learning/           # Parameter inference - Bayesian learning
│   ├── pruning/            # Global inference - MaxSMT selection
│   ├── integration/        # Solver integrations (Z3, Kiwi)
│   ├── scraping/           # Web scraping for extracting layouts
│   ├── display/            # Visualization templates
│   ├── run.py              # Main synthesis pipeline
│   ├── cli.py              # Command-line interface
│   └── app.py              # Web API server
├── tests/                  # Test suite
├── etc/                    # Additional resources (notebooks)
└── stubs/                  # Type stubs for external libraries
```

---

## Core Modules

### 1. Entry Points

#### `run.py` - Main Synthesis Pipeline
**Purpose**: Orchestrates the complete Mockdown synthesis pipeline.

**Key Functions**:
- `run(input_data, options)` - Main entry point that executes the full pipeline:
  1. Load examples using `ViewLoader`
  2. Instantiate templates using chosen instantiator (Prolog or Numpy)
  3. Learn parameters using chosen learning method (Simple, Heuristic, or NoiseTolerant)
  4. Prune constraints using chosen pruning method (None, Baseline, or Hierarchical)
  5. Return synthesized constraints as JSON

- `run_timeout()` - Wrapper that runs synthesis with timeout using multiprocessing

**Configuration Options** (via `MockdownOptions`):
- `input_format`: 'default' or 'bench' (different JSON formats)
- `numeric_type`: 'N' (Number), 'R' (Real), 'Q' (Rational), 'Z' (Integer)
- `instantiation_method`: 'prolog' or 'numpy'
- `learning_method`: 'simple', 'heuristic', or 'noisetolerant'
- `pruning_method`: 'none', 'baseline', or 'hierarchical'
- `pruning_bounds`: Test screen size bounds (min_w, min_h, max_w, max_h)
- Debug options for intermediate outputs

#### `cli.py` - Command-Line Interface
**Purpose**: Provides command-line tools for running Mockdown.

**Commands**:
- `mockdown run` - Run synthesis on input JSON
- `mockdown scrape` - Scrape layouts from web pages using Selenium
- `mockdown display` - Visualize layouts in a web browser
- `mockdown serve` - Start web API server

**Example Usage**:
```bash
# Run synthesis
mockdown run input.json output.json --learning-method noisetolerant --pruning-method hierarchical

# Scrape a website
mockdown scrape https://example.com output.json --dims 1280 800

# Visualize results
mockdown display results.json
```

#### `app.py` - Web API Server
**Purpose**: Starlette-based web server exposing synthesis as REST API.

**Endpoints**:
- `POST /api/synthesize` - Run synthesis on JSON input
  - Request body: `{ examples: [...], options: {...} }`
  - Response: `{ constraints: [...], axioms: [...] }`

Uses CORS middleware to allow cross-origin requests.

---

### 2. Model - Data Structures (`src/mockdown/model/`)

This module defines the core data structures representing UI layouts.

#### `model/view/view.py` - View Class
**Purpose**: Represents a UI element (box) in the layout hierarchy.

**Key Classes**:
- `View` - Main implementation of `IView` protocol
  - `name`: Unique identifier (e.g., "header", "sidebar")
  - `rect`: Bounding box (left, top, right, bottom)
  - `children`: List of child views
  - `parent`: Reference to parent view

**Key Properties**:
- Anchor properties: `left_anchor`, `right_anchor`, `top_anchor`, `bottom_anchor`, `width_anchor`, `height_anchor`, `center_x_anchor`, `center_y_anchor`
- Edge properties: Pairs of (anchor, interval) representing edges
- Navigation: `find_view()`, `find_anchor()`, `is_parent_of()`, `is_sibling_of()`
- Iteration: Views are iterable, yielding self and all descendants

**Design Notes**:
- Uses frozen dataclass for immutability
- Generic over numeric type `NT` (supports integers, rationals, floats via sympy)
- Implements `IRect` interface by delegation to internal `rect` field

#### `model/anchor.py` - Anchor Class
**Purpose**: Represents a specific attribute of a view (e.g., "header.left", "sidebar.width").

**Key Classes**:
- `AnchorID` - Unique identifier for an anchor
  - `view_name`: Name of the view
  - `attribute`: One of {left, right, top, bottom, width, height, center_x, center_y}

- `Anchor` - Links a view to a specific attribute
  - `view`: Reference to the view
  - `attribute`: Which dimension this anchor represents
  - `value`: Numeric value of this attribute (computed from view.rect)
  - `edge`: Associated edge (for position anchors)

**Example**:
```python
# If view.name = "header" and view.rect = Rect(0, 0, 100, 50)
header.left_anchor.id    # AnchorID("header", Attribute.LEFT)
header.left_anchor.value # 0
header.width_anchor.value # 100
```

#### `model/edge.py` - Edge Class
**Purpose**: Represents an edge of a view along one axis.

**Structure**:
- `anchor`: The anchor defining the edge position
- `interval`: Range perpendicular to the edge (e.g., for left edge, interval is (top, bottom))

Edges are used in the visibility graph computation.

#### `model/primitives/`
**Purpose**: Fundamental types and geometry.

**Files**:
- `attribute.py` - `Attribute` enum defining 8 anchor types
  - Position: LEFT, TOP, RIGHT, BOTTOM, CENTER_X, CENTER_Y
  - Size: WIDTH, HEIGHT
  - Helper methods: `is_size()`, `is_position()`, `is_horizontal()`, `is_vertical()`
  - `is_dual_pair()` - Check if two attributes are dual (e.g., top/bottom, left/right)

- `geometry.py` - `Rect` dataclass
  - Stores bounding box as (left, top, right, bottom)
  - Computed properties: `width`, `height`, `center_x`, `center_y`

- `identifiers.py` - Type aliases for view names

#### `model/view/loader.py` - ViewLoader
**Purpose**: Parse JSON into View hierarchy.

**Key Methods**:
- `load_dict(data)` - Load from dictionary
- `load_file(src)` - Load from file

**Supported Formats**:
- **Default format**: `{ name: "root", rect: [l, t, r, b], children: [...] }`
- **Bench format**: `{ name: "root", left: l, top: t, width: w, height: h, children: [...] }`

**Features**:
- Supports adding Gaussian noise for testing (`debug_noise` parameter)
- Generic over numeric type (can load as integers, rationals, or floats)

#### `model/view/builder.py` - ViewBuilder
**Purpose**: Builder pattern for constructing View hierarchies.

Separates the parsing phase (creating builders with raw numeric data) from the construction phase (converting to typed Views). This enables dependent typing where the numeric type is determined at build time.

---

### 3. Constraints (`src/mockdown/constraint/`)

This module defines constraint representations.

#### `constraint/types.py` - Constraint Type System
**Purpose**: Define constraint kinds and protocols.

**Key Enums**:
- `ConstraintKind` - Categorizes constraints by form and semantics:
  - **Position constraints**:
    - `POS_LTRB_OFFSET`: `y = x + b` (e.g., `sidebar.top = header.bottom + 0`)
    - `POS_CENTERING`: `y = x` (e.g., `child.center_x = parent.center_x`)
  
  - **Size constraints**:
    - `SIZE_CONSTANT`: `y = b` (e.g., `header.height = 80`)
    - `SIZE_CONSTANT_BOUND`: Like SIZE_CONSTANT but lower priority (for noisy data)
    - `SIZE_OFFSET`: `y = x + b` (e.g., `child.width = parent.width + (-20)`)
    - `SIZE_RATIO`: `y = a·x` (e.g., `child.width = 0.5 · parent.width`)
    - `SIZE_RATIO_GENERAL`: `y = a·x + b` (rare, general form)
    - `SIZE_ASPECT_RATIO`: `y = a·x` where x and y are different dimensions (e.g., `width = 1.5 · height`)
    - `SIZE_ASPECT_RATIO_GENERAL`: General form of aspect ratio

**Classification Properties**:
- `is_constant_form`: No x variable (just `y = b`)
- `is_add_only_form`: Only b is unknown (`y = x + b`)
- `is_mul_only_form`: Only a is unknown (`y = a·x`)
- `is_general_form`: Both a and b unknown (`y = a·x + b`)
- `is_position_kind`: Constrains positions
- `is_size_kind`: Constrains sizes
- `num_free_vars`: Returns 0, 1, or 2 depending on form

**Priority System**:
- `PRIORITY_REQUIRED`: (1000, 1000, 1000) - Hard constraints
- `PRIORITY_STRONG`: (1, 0, 0)
- `PRIORITY_MEDIUM`: (0, 1, 0)
- `PRIORITY_WEAK`: (0, 0, 1)

Priorities used by Kiwi solver for soft constraints.

#### `constraint/constraint.py` - Constraint Implementations
**Purpose**: Concrete constraint classes.

**Classes**:
- `ConstantConstraint` - Implements `y = b`
  - Fields: `y_id`, `b`, `op`, `priority`, `sample_count`, `is_falsified`
  - `x_id` and `a` are fixed to None and 0

- `LinearConstraint` - Implements `y = a·x + b`
  - Fields: `y_id`, `x_id`, `a`, `b`, `op`, `priority`, `sample_count`, `is_falsified`

**Key Methods**:
- `subst(a, b, sample_count)` - Instantiate template with learned parameters
- `to_dict()` - Export to JSON
- `to_expr()` - Convert to sympy expression
- `is_template` property - True if sample_count == 0 (not yet learned)

**Comparison Operators**:
- `op` field can be `operator.eq`, `operator.le`, or `operator.ge`
- Enables expressing inequalities for bounds

#### `constraint/factory.py` - ConstraintFactory
**Purpose**: Factory for creating constraint instances.

**Method**:
- `create(kind, y_id, x_id=None, op=None)` - Create appropriate constraint subclass based on kind

Uses constraint kind to determine whether to create `ConstantConstraint` or `LinearConstraint`.

#### `constraint/axioms.py` - Layout Axioms
**Purpose**: Generate universal geometric axioms (e.g., width = right - left).

Currently returns empty list - axioms are handled implicitly in solver integrations.

---

### 4. Instantiation - Local Inference (`src/mockdown/instantiation/`)

This module implements the first phase: generating candidate constraint templates.

#### `instantiation/numpy/instantiator.py` - NumpyConstraintInstantiator
**Purpose**: Fast, vectorized template instantiation using NumPy/Pandas.

**Algorithm**:
1. Build anchor relationship matrices:
   - `same_view_mat`: Anchors from same view
   - `parent_mat`: Parent-child relationships
   - `sibling_mat`: Sibling relationships
   - `visible_mat`: Visibility graph (see below)
   - `both_size_mat`, `both_pos_mat`: Type compatibility
   - `both_h_mat`, `both_v_mat`: Axis alignment
   - `same_attr_mat`, `dual_attr_mat`: Attribute relationships

2. Combine matrices to identify valid constraint patterns:
   - **Aspect ratios**: Same view, size attributes, horizontal × vertical
   - **Parent-relative size**: Parent-child, both sizes, same axis
   - **Sibling-relative size**: Siblings, sizes, same attr, visible
   - **Absolute sizes**: Any size attribute
   - **Offset positions**: Parent-child or sibling dual positions, visible
   - **Align positions**: Siblings, same position attribute, visible

3. Generate constraint templates for each valid pattern

**Advantages**:
- Fast: Uses vectorized NumPy operations
- No external dependencies (unlike Prolog version)
- Default instantiation method

#### `instantiation/prolog/instantiator.py` - PrologConstraintInstantiator
**Purpose**: Logic programming-based instantiation using SWI-Prolog via PySwip.

Uses Prolog rules in `logic.pl` to encode constraint validity rules declaratively. Less commonly used due to PySwip dependency.

#### `instantiation/visibility.py` - Visibility Graph
**Purpose**: Compute which anchor pairs can "see" each other.

**Key Function**: `visible_pairs(view, deep=True)`

**Algorithm** (Sweep-line):
1. Build interval trees for horizontal and vertical edges
2. For each vertical line (x-coordinate of any edge):
   - Query all horizontal edges it intersects
   - Sort by y-position
   - Adjacent edges in sorted order are visible to each other
3. For each horizontal line (y-coordinate):
   - Query all vertical edges it intersects
   - Sort by x-position
   - Adjacent edges in sorted order are visible

4. Recursively compute visibility for child views

**Purpose of Visibility**:
- Prunes unrealistic constraints (e.g., relating anchors of disconnected UI elements)
- Based on intuition that UI elements are typically positioned relative to nearby elements

**Example**:
```
+----------------+
|  Header        |
+------+----+----+
| Side | Main   |
| bar  |        |
+------+--------+
```
Visible pairs include:
- `(header.bottom, sidebar.top)`
- `(header.bottom, main.top)`
- `(sidebar.right, main.left)`

But NOT:
- `(header.left, main.right)` - No line of sight without passing through another edge

#### `instantiation/normalization.py`
**Purpose**: Normalize constraint multipliers (currently unused).

Provides `normalize_multiplier()` function that could standardize constraint forms.

---

### 5. Learning - Parameter Inference (`src/mockdown/learning/`)

This module implements parameter learning for constraint templates.

#### `learning/noisetolerant/learning.py` - NoiseTolerantLearning
**Purpose**: Bayesian parameter inference robust to noisy examples.

**Algorithm** (for each template):
1. Extract training data from examples
2. Perform linear regression to get point estimate and confidence interval
3. Generate candidate parameter values:
   - For `a` (multiplicative): Rational numbers in confidence interval, scored by Stern-Brocot depth
   - For `b` (additive): Integers in confidence interval, scored uniformly
4. Compute Bayesian posterior for each candidate:
   - Prior: `P(a)` or `P(b)` based on simplicity
   - Likelihood: `P(data | param)` based on fit quality (Gaussian noise model)
   - Posterior: `P(param | data) ∝ P(param) · P(data | param)`
5. Return top candidates sorted by posterior probability

**Key Classes**:
- `NoiseTolerantLearning` - Main learning class
  - `learn()` - Process all templates (optionally in parallel)
  - `learn_one(template)` - Learn single template
  - `_template_data(template)` - Extract x,y data for template

- `NoiseTolerantTemplateModel` - Model for single template
  - Performs linear regression using `statsmodels`
  - Handles single-example case by adding synthetic data point
  - Adds tiny noise to avoid perfect fit issues
  - `reject()` - Reject template if poor fit (high p-value or spread)
  - `learn()` - Return scored candidates
  - `candidates()` - Generate parameter space

**Configuration** (`NoiseTolerantLearningConfig`):
- `cutoff_fit`: Reject if goodness-of-fit p-value < 0.05
- `cutoff_spread`: Reject if standard deviation > 3
- `max_offset`: Maximum absolute value for b (default 1000)
- `max_denominator`: Maximum denominator for rationals (default 100)
- `expected_depth`: Expected Stern-Brocot depth for prior (default 5)
- `a_alpha`, `b_alpha`: Confidence interval alpha levels

#### `learning/noisetolerant/math.py` - Mathematical Utilities
**Purpose**: Helper functions for Bayesian priors.

**Key Functions**:
- `continued_fraction(a)` - Compute continued fraction representation
- `sb_depth(a)` - Stern-Brocot tree depth (sum of continued fraction terms)
- `farey(n)` - Generate Farey sequence (rationals with denominator ≤ n)
- `ext_farey(n)` - Extended Farey sequence (includes ±∞)
- `z_ball(center, radius)` - Integer ball around center

**Stern-Brocot Depth**:
- Measures "simplicity" of rational number
- Simple fractions like 1/2, 1/3 have low depth
- Complex fractions like 47/83 have high depth
- Used as prior: `P(a) ∝ exp(-depth(a))`

#### `learning/simple.py` - SimpleLearning
**Purpose**: Simpler learning method without Bayesian inference.

**Algorithm**:
1. For each template, compute linear regression
2. Round results to "simple" values:
   - Constants: Round to nearest integer
   - Ratios: Rationalize to nearest simple fraction
3. Check if constraints approximately hold on all examples

**Classes**:
- `SimpleLearning` - Basic learning
- `HeuristicLearning` - Extends SimpleLearning with heuristic scoring

Faster but less robust to noise than NoiseTolerantLearning.

#### `learning/types.py` - Learning Interfaces
**Purpose**: Protocol definitions.

**Protocols**:
- `IConstraintLearning` - Learning method interface
  - `learn()` → `List[List[ConstraintCandidate]]`

**Data Classes**:
- `ConstraintCandidate` - Learned constraint with score
  - `constraint`: Instantiated constraint (with a, b values)
  - `score`: Likelihood/posterior probability

---

### 6. Pruning - Global Inference (`src/mockdown/pruning/`)

This module implements MaxSMT-based constraint selection.

#### `pruning/blackbox.py` - BlackBoxPruner
**Purpose**: Baseline pruning method using monolithic MaxSMT query.

**Algorithm**:
1. Create Z3 Optimize solver
2. For each test screen size and each constraint:
   - Create boolean control variable `b_i`
   - Add soft assertion: `b_i ⇒ constraint_i` with weight from learning score
3. Add hard axioms:
   - Root size matches screen size
   - Width/height definitions: `w = r - l`, `h = b - t`
   - Center definitions: `cx = (l + r) / 2`, `cy = (t + b) / 2`
   - Containment: Children within parents
   - Non-negativity: All positions ≥ 0

4. Add determinism constraints:
   - Each dimension determined by at most 1 constraint
   - Each box has exactly 2 horizontal dimensions determined (e.g., left + width)
   - Each box has exactly 2 vertical dimensions determined (e.g., top + height)

5. Add linking constraints (optional):
   - For each layer, at least two children must be externally determined
   - Prevents under-constrained layouts

6. Solve MaxSMT: Maximize number of satisfied soft constraints
7. Extract selected constraints where `b_i = true`

**Limitations**:
- Scales poorly with large layouts (too many variables)
- Solved by HierarchicalPruner below

#### `pruning/blackbox.py` - HierarchicalPruner
**Purpose**: Decomposed pruning using hierarchical solver invocations (implements algorithm from paper).

**Algorithm** (WorkList-based):
```python
worklist = [(root, test_dims)]
selected_constraints = set()

while worklist:
    focus_view, focus_dims = worklist.pop()
    
    # 1. Filter to constraints for immediate children of focus_view
    relevant = [c for c in candidates if relevant_constraint(focus_view, c)]
    
    # 2. Solve MaxSMT for this focus_view and its children
    selected = solve_maxsmt(relevant, focus_view, focus_dims)
    selected_constraints.update(selected)
    
    # 3. For each child, infer its dimension ranges
    for child in focus_view.children:
        child_dims = infer_child_dims(focus_view, focus_dims, child, selected)
        worklist.append((child, child_dims))

return selected_constraints
```

**Key Methods**:
- `relevant_constraint(focus, c)` - Check if constraint affects focus view's immediate children
- `infer_child_confs()` - Use MaxSMT to find min/max dimensions for child
  - Minimize/maximize each dimension subject to selected parent constraints
  - Returns `(min_conf, max_conf)` for child
- `confs_to_constrs()` - Convert conformances to test dimensions

**Advantages**:
- Scales to large layouts by decomposition
- Each subproblem involves only parent + immediate children
- Test dimensions naturally propagate down hierarchy

#### `pruning/conformance.py` - Conformance Type
**Purpose**: Represents a concrete screen size configuration.

**Structure**:
```python
@dataclass
class Conformance:
    width: Fraction
    height: Fraction
    x: Fraction       # left position
    y: Fraction       # top position
```

Used to specify test screen sizes for MaxSMT queries.

**Key Functions**:
- `conformance_range(lower, upper, scale)` - Generate interpolated test points
- `from_rect(rect)` - Convert Rect to Conformance
- `to_rect(conf)` - Convert Conformance to Rect
- `add_conf_dims(solver, conf, idx, targets)` - Add conformance as Z3 constraints

#### `pruning/types.py` - Pruning Types
**Purpose**: Common types and base class.

**Types**:
- `ISizeBounds` - Test bounds configuration
  - `min_w`, `max_w`, `min_h`, `max_h`: Optional bounds
  - `min_x`, `max_x`, `min_y`, `max_y`: Optional position bounds

- `IPruningMethod` - Pruning method protocol

**Base Class**:
- `BasePruningMethod` - Shared utilities
  - `whole_score(c)` - Score constraint by parameter simplicity
  - `build_biases(candidates)` - Extract scores from learning
  - `add_containment_axioms()` - Add parent-child containment to Z3
  - `add_layout_axioms()` - Add width/height/center definitions to Z3
  - `filter_constraints()` - Remove redundant inequality constraints
  - `combine_bounds()` - Merge complementary inequality constraints

#### `pruning/util.py` - Utilities
**Purpose**: Helper functions.

**Key Functions**:
- `short_str(cn)` - Compact constraint string
- `anchor_equiv(c1, c2)` - Check if constraints affect same anchor
- `to_frac(x)` - Convert numeric to Fraction
- `round_up(x, places)`, `round_down(x, places)` - Rounding utilities

---

### 7. Integration - Solver Integrations (`src/mockdown/integration/`)

This module provides bindings to constraint solvers.

#### `integration/z3.py` - Z3 Integration
**Purpose**: Interface to Z3 SMT solver for MaxSMT pruning.

**Key Functions**:
- `anchor_id_to_z3_var(anchor_id, suffix)` - Create Z3 real variable
  - Format: `"viewname.attribute_idx"`
  - Suffix allows multiple conformances

- `constraint_to_z3_expr(constraint, suffix)` - Convert constraint to Z3 formula
  - `y = a·x + b` becomes `y_i == a * x_i + b` (for conformance i)
  - Supports equality and inequality operators

- `extract_model_valuations(model, idx, names)` - Extract values from Z3 model
  - Returns dictionary mapping anchor names to rational values

- `load_view_from_model(model, idx, skeleton)` - Reconstruct View from Z3 solution
  - Walks view tree and populates rectangles from model values

**Usage in Pruning**:
```python
solver = z3.Optimize()

# Add soft constraints (can be violated)
for i, constraint in enumerate(candidates):
    b_i = z3.Bool(f"b_{i}")
    solver.add_soft(z3.Implies(b_i, constraint_to_z3_expr(constraint, 0)),
                    weight=constraint.score)

# Add hard constraints (must be satisfied)
solver.add(root.width == screen_width)
solver.add(root.height == screen_height)

# Solve and extract
if solver.check() == z3.sat:
    model = solver.model()
    selected = [c for i, c in enumerate(candidates) if model[b_i]]
```

#### `integration/kiwi.py` - Kiwi Integration
**Purpose**: Interface to Cassowary constraint solver (via kiwisolver) for layout evaluation.

**Key Functions**:
- `make_kiwi_env(view)` - Create Kiwi variables for all anchors

- `constraint_to_kiwi(constraint, env, strength)` - Convert constraint to Kiwi constraint
  - Handles rational coefficients by cross-multiplication
  - Example: `y = (2/3)x + (1/2)` becomes `6y = 4x + 3`

- `add_linear_axioms(solver, targets, env)` - Add geometric axioms
  - `width = right - left`
  - `height = bottom - top`
  - `center_x = (left + right) / 2`
  - `center_y = (top + bottom) / 2`
  - Non-negativity: All values ≥ 0

- `add_linear_containment(solver, env, parent)` - Add containment constraints
  - Children must be within parent bounds

- `evaluate_constraints(view, top_rect, constraints, strength)` - Solve and extract layout
  - Creates solver, adds axioms and constraints
  - Fixes top-level rectangle
  - Solves system
  - Returns View with computed positions

**Usage**:
```python
# Synthesize constraints
constraints = mockdown_synthesis(examples)

# Test on new screen size
new_screen = Rect(0, 0, 1920, 1080)
result_view = evaluate_constraints(examples[0], new_screen, constraints)

# result_view now contains layout at 1920x1080
```

**Kiwi vs Z3**:
- **Z3**: Used for MaxSMT constraint selection (discrete optimization)
- **Kiwi**: Used for continuous constraint solving (layout evaluation)
- Kiwi is faster for continuous solving but lacks MaxSMT capabilities

---

### 8. Scraping (`src/mockdown/scraping/`)

#### `scraping/scraper.py` - Scraper
**Purpose**: Extract layout hierarchies from live web pages.

**Implementation**:
- Uses Selenium WebDriver (Chrome) to load pages
- Injects JavaScript payload into page
- JavaScript walks DOM tree and extracts:
  - Element names (tag + id + classes)
  - Bounding rectangles (via `getBoundingClientRect()`)
  - Hierarchy structure

**Key Methods**:
- `scrape(url, dims, root_selector)` - Scrape single screen size
  - Opens browser at specified dimensions
  - Navigates to URL
  - Executes JavaScript payload
  - Returns JSON layout hierarchy

**Filtering**:
- Excludes elements matching selectors (e.g., `p > *` to skip text nodes)
- Excludes invisible elements (width or height = 0)
- Excludes disjoint elements (not overlapping parent)

**Output Format**:
```json
{
  "name": "[div.header@1]",
  "rect": [0, 0, 1200, 80],
  "children": [...]
}
```

**Use Case**:
```bash
# Scrape at multiple screen sizes
mockdown scrape https://example.com --dims 1280 800 > example_1280x800.json
mockdown scrape https://example.com --dims 1920 1080 > example_1920x1080.json

# Combine into training set
{ "examples": [ ... ] }

# Run synthesis
mockdown run combined.json output.json
```

---

### 9. Display (`src/mockdown/display/`)

#### `display/templates/` - Visualization
**Purpose**: HTML/JS templates for visualizing layouts.

**Files**:
- `default.html.jinja2` - Main template
  - Renders layout examples side-by-side
  - Uses Kiwi solver (JS version) to animate constraints
  - Interactive: Can adjust screen size and see layout update

- `js/flightlessbird.all.js` - JavaScript Kiwi solver
  - Port of Cassowary algorithm to JavaScript
  - Enables client-side constraint solving

**Usage**:
```bash
mockdown display input.json
# Opens browser with interactive visualization
```

Visualization shows:
- All example layouts
- Bounding boxes with names
- Color-coded by example
- Can be useful for debugging synthesis issues

---

### 10. Tests (`tests/`)

#### Test Structure
```
tests/
├── model/
│   └── test_view.py           # View isomorphism tests
├── inferui/
│   ├── onetwo.json            # Test fixture
│   └── test_onetwo.py         # End-to-end test
├── test_builder.py            # ViewBuilder tests
└── test_loader.py             # ViewLoader tests
```

**Key Tests**:
- `test_view.py::test_view_is_isomorphic` - Verify view comparison logic
- `test_builder.py::test_dependent_typing` - Verify generic numeric types work
- `test_loader.py::test_loading_ints` - Verify JSON parsing

**Running Tests**:
```bash
pytest tests/
```

---

## Key Design Patterns

### 1. Generic Numeric Types
The codebase is heavily generic over numeric type `NT`:
- `View[NT]`, `Anchor[NT]`, `Edge[NT]`, `Rect[NT]`
- Supports `sympy.Integer`, `sympy.Rational`, `sympy.Float`, `sympy.Number`
- Enables exact rational arithmetic (important for reproducibility)

**Pattern**:
```python
from typing import TypeVar
NT = TypeVar('NT', bound=sym.Number)

class View(Generic[NT]):
    rect: Rect[NT]
    
    def width(self) -> NT:
        return self.rect.right - self.rect.left
```

### 2. Protocol-Based Interfaces
Uses Python protocols (structural typing) for interfaces:
- `IView`, `IAnchor`, `IEdge`, `IConstraint`
- Enables duck typing and easier testing

**Pattern**:
```python
from typing import Protocol

class IConstraint(Protocol):
    y_id: IAnchorID
    x_id: Optional[IAnchorID]
    a: sym.Rational
    b: sym.Rational
    
    def subst(self, a, b) -> IConstraint: ...
```

### 3. Factory Pattern
`ConstraintFactory` abstracts constraint creation:
```python
ConstraintFactory.create(
    kind=ConstraintKind.SIZE_RATIO,
    y_id=child_width,
    x_id=parent_width
)
# Returns appropriate subclass based on kind
```

### 4. Strategy Pattern
Pluggable algorithms via configuration:
- Instantiation: `NumpyConstraintInstantiator` vs `PrologConstraintInstantiator`
- Learning: `SimpleLearning` vs `NoiseTolerantLearning`
- Pruning: `BlackBoxPruner` vs `HierarchicalPruner`

All implement common protocol, selected at runtime.

### 5. Visitor Pattern
View traversal via iteration protocol:
```python
for view in root:  # Visits root and all descendants
    print(view.name, view.rect)
```

### 6. Builder Pattern
`ViewBuilder` separates parsing from construction:
```python
builder = ViewBuilder(name="root", rect=(0, 0, 100, 100))
view_int = builder.build(number_type=sym.Integer)
view_rat = builder.build(number_type=sym.Rational)
```

---

## Data Flow

### Complete Synthesis Pipeline

```
Input JSON Examples
    ↓
[ViewLoader]
    ↓
List[IView] (typed examples)
    ↓
[ConstraintInstantiator] (NumpyConstraintInstantiator)
    |
    ├─> Compute visibility graph (visible_pairs)
    ├─> Generate anchor relationship matrices
    └─> Instantiate constraint templates
    ↓
List[IConstraint] (templates with sample_count=0)
    ↓
[ConstraintLearning] (NoiseTolerantLearning)
    |
    ├─> Extract training data for each template
    ├─> Perform linear regression
    ├─> Generate candidate parameters (Farey sequence for a, integers for b)
    ├─> Score by Bayesian posterior
    └─> Return top candidates per template
    ↓
List[ConstraintCandidate] (constraints with scores)
    ↓
[PruningMethod] (HierarchicalPruner)
    |
    ├─> Initialize worklist with (root, test_dims)
    ├─> While worklist not empty:
    │   ├─> Pop (focus_view, focus_dims)
    │   ├─> Filter relevant constraints
    │   ├─> Solve MaxSMT (Z3) for focus_view's children
    │   ├─> Select constraints where b_i = true
    │   ├─> For each child:
    │   │   ├─> Infer child dimension range via Z3
    │   │   └─> Add (child, child_dims) to worklist
    │   └─> Continue
    └─> Return all selected constraints
    ↓
List[IConstraint] (final synthesized constraints)
    ↓
Output JSON
```

### Evaluation Pipeline

```
Synthesized Constraints + New Screen Size
    ↓
[KiwiSolver]
    |
    ├─> Create Kiwi variables for all anchors
    ├─> Add layout axioms (width = right - left, etc)
    ├─> Add containment axioms (children in parents)
    ├─> Add synthesized constraints
    ├─> Fix root dimensions to new screen size
    ├─> Solve system
    └─> Extract variable values
    ↓
IView[sym.Float] (layout at new screen size)
```

---

## Important Implementation Details

### 1. Determinism Constraints in MaxSMT

The pruner ensures each view dimension is fully determined:
- Each dimension has **at most one** constraint (uniqueness)
- Each view has **exactly two** horizontal dimensions determined (e.g., left + width OR left + right OR width + right)
- Each view has **exactly two** vertical dimensions determined

This prevents:
- Over-constrained layouts (conflicting constraints)
- Under-constrained layouts (ambiguous positions)

### 2. Linking Constraints

For each layer in hierarchy:
- At least **two children** must be externally determined (by parent)
- Prevents circular dependencies where all children only reference each other

### 3. Visibility Graph Pruning

Reduces search space significantly:
- For N views with 8 anchors each: 8N anchors
- Naive: Consider all (8N)² = 64N² anchor pairs
- With visibility: Typically O(N) pairs (only adjacent edges visible)

For 10 views:
- Naive: 6,400 pairs
- Visibility: ~40 pairs (160x reduction!)

### 4. Bayesian Learning Robustness

**Noise Tolerance**:
- Linear regression gives point estimate
- Confidence interval captures uncertainty
- Prior favors simple values
- Example: Given data near 0.49, 0.51, posterior peaks at exactly 0.5

**Single Example Handling**:
- Can't do regression with 1 point
- Solution: Add synthetic second point based on constraint kind
- For `y = x + b`: Add point `(0, original_y - original_x)`
- For `y = a·x`: Add point `(0, 0)` (forces line through origin)
- For `y = b`: Add point `(0, original_y)` (constant)

### 5. Hierarchical Decomposition

**Why Needed**:
- Monolithic MaxSMT for 50+ views: 400+ anchors, 1000+ constraints
- Z3 query can take minutes or timeout

**Solution**:
- Break into subproblems: 1 parent + children (typically 2-5 views)
- Each subproblem: 16-40 anchors, 20-50 constraints
- Z3 solves in milliseconds
- Total time: Linear in hierarchy depth (typically 3-5 levels)

**Trade-off**:
- May not find global optimum (greedy decomposition)
- But much faster and scales to large layouts
- In practice: Results are good (local optima are often global)

---

## Configuration Reference

### Command-Line Options

```bash
mockdown run INPUT OUTPUT [OPTIONS]

Options:
  -if, --input-format [default|bench]
      Input JSON format (default: default)
  
  -nt, --numeric-type [N|R|Q|Z]
      Numeric type: Number, Real, Rational, Integer (default: N)
  
  -im, --instantiation-method [prolog|numpy]
      Instantiation algorithm (default: numpy)
  
  -lm, --learning-method [simple|heuristic|noisetolerant]
      Parameter learning algorithm (default: noisetolerant)
  
  -pm, --pruning-method [none|baseline|hierarchical]
      Constraint selection method (default: hierarchical)
  
  -pb, --pruning-bounds MIN_W MIN_H MAX_W MAX_H
      Test screen size bounds (use - for unspecified)
      Example: -pb 800 600 1920 1080
  
  -dn, --debug-noise STDEV
      Add Gaussian noise to input (for testing)
  
  -dv, --debug-visibilities
      Output visibility graph only
  
  -di, --debug-instantiation
      Output constraint templates only (no learning/pruning)
  
  -to, --timeout SECONDS
      Abort synthesis after timeout
  
  -n, --num-examples COUNT
      Use only first N examples
```

### API Options

```python
from mockdown.run import run_timeout

result = run_timeout(
    input_data={
        "examples": [
            {"name": "root", "rect": [0, 0, 800, 600], "children": [...]},
            {"name": "root", "rect": [0, 0, 1200, 800], "children": [...]}
        ]
    },
    options={
        "numeric_type": "Q",          # Use rationals
        "learning_method": "noisetolerant",
        "pruning_method": "hierarchical",
        "pruning_bounds": (800, 600, 1920, 1080),
        "debug": False
    },
    timeout=60  # seconds
)

# result = {
#     "constraints": [
#         {"y": "header.height", "op": "=", "b": "80", ...},
#         {"y": "sidebar.width", "op": "=", "b": "250", ...},
#         ...
#     ],
#     "axioms": [...]
# }
```

---

## Extension Points

### Adding a New Constraint Kind

1. Add to `ConstraintKind` enum in `constraint/types.py`:
```python
class ConstraintKind(Enum):
    MY_NEW_KIND = 'my_new_kind'
```

2. Classify it (add to appropriate sets):
```python
ConstraintKind.add_only_forms = frozenset({..., ConstraintKind.MY_NEW_KIND})
```

3. Update instantiator to generate templates of this kind:
```python
# In NumpyConstraintInstantiator.instantiate()
for pair in self.anchor_mat[my_condition_mat.astype(np.bool)].stack():
    yield ConstraintFactory.create(
        kind=ConstraintKind.MY_NEW_KIND,
        y_id=pair[0].id,
        x_id=pair[1].id
    )
```

### Adding a New Learning Method

1. Implement `IConstraintLearning` protocol:
```python
class MyLearning(IConstraintLearning):
    def __init__(self, templates, samples, config):
        self.templates = templates
        self.samples = samples
    
    def learn(self) -> List[List[ConstraintCandidate]]:
        return [self.learn_one(t) for t in self.templates]
    
    def learn_one(self, template) -> List[ConstraintCandidate]:
        # Your learning logic here
        return [ConstraintCandidate(constraint=..., score=...)]
```

2. Register in `run.py`:
```python
learning_factory = {
    'simple': SimpleLearning,
    'heuristic': HeuristicLearning,
    'noisetolerant': NoiseTolerantLearning,
    'mylearning': MyLearning
}[options.get('learning_method')]
```

3. Add CLI option in `cli.py`

### Adding a New Pruning Method

1. Implement `IPruningMethod` protocol:
```python
class MyPruner(BasePruningMethod):
    def __init__(self, examples, bounds, unambig):
        self.examples = examples
        self.bounds = bounds
    
    def __call__(self, candidates: List[ConstraintCandidate]) -> 
            Tuple[List[IConstraint], Dict, Dict]:
        # Your pruning logic here
        return selected_constraints, {}, {}
```

2. Register in `run.py`
3. Add CLI option

---

## Common Issues and Debugging

### Issue: Synthesis Times Out

**Causes**:
- Too many views (>50)
- Too many examples (>10)
- Baseline pruner with large layout

**Solutions**:
- Use hierarchical pruner: `--pruning-method hierarchical`
- Reduce examples: `--num-examples 3`
- Increase timeout: `--timeout 300`

### Issue: Poor Quality Constraints

**Symptoms**:
- Constraints don't generalize to new screen sizes
- Too many constant constraints

**Causes**:
- Examples too similar (not enough variation)
- Examples too noisy

**Solutions**:
- Provide more diverse examples (different screen sizes)
- Use noisetolerant learning: `--learning-method noisetolerant`
- Check visibility graph: `--debug-visibilities`

### Issue: Over-Constrained Layout

**Symptoms**:
- Kiwi solver reports unsatisfiable constraints
- Layout looks broken at new screen size

**Causes**:
- Conflicting constraints selected

**Solutions**:
- Check determinism is being enforced (should be automatic)
- Inspect synthesized constraints manually
- Try baseline pruner to see if hierarchical decomposition is the issue

### Issue: Under-Constrained Layout

**Symptoms**:
- Some elements at position 0 or have size 0
- Layout incomplete

**Causes**:
- Pruner didn't select enough constraints
- Visibility graph too restrictive

**Solutions**:
- Check `--debug-instantiation` - are templates being generated?
- Visualize with `mockdown display` - are examples reasonable?
- Lower learning cutoffs in `NoiseTolerantLearningConfig`

### Debugging Workflow

1. **Check inputs**:
```bash
mockdown display input.json
# Verify examples look correct
```

2. **Check visibility**:
```bash
mockdown run input.json out.json --debug-visibilities
# Inspect visibility pairs
```

3. **Check templates**:
```bash
mockdown run input.json out.json --debug-instantiation
# How many templates generated? Expected 10-100 for typical layout
```

4. **Check learning**:
```bash
# Add logging
LOGLEVEL=DEBUG mockdown run input.json out.json
# Look for rejected templates
```

5. **Check pruning**:
```bash
# Disable pruning to see all learned constraints
mockdown run input.json out.json --pruning-method none
```

---

## Performance Characteristics

### Time Complexity

**Instantiation** (NumpyConstraintInstantiator):
- Visibility: O(N² log N) where N = number of anchors
- Matrix operations: O(N²)
- Total: O(N²) where N is typically 8 × number of views

**Learning** (NoiseTolerantLearning):
- Per template: O(M²) for linear regression where M = number of examples
- Candidate generation: O(D × B) where D = max_denominator, B = max_offset
- Total: O(T × (M² + D × B)) where T = number of templates

**Pruning** (HierarchicalPruner):
- Per subproblem: O(2^C) where C = constraints for parent + children (typically 20-50)
- Number of subproblems: O(V) where V = number of views
- Total: O(V × 2^50) per subproblem, but Z3 heuristics make this practical

### Space Complexity

**Instantiation**: O(N²) for anchor relationship matrices

**Learning**: O(T × M) for template data

**Pruning**: O(V × C × K) where K = number of conformances (test screen sizes)

### Typical Performance

For a layout with 10 views, 3 examples:
- Instantiation: <0.1s (50-100 templates)
- Learning: 0.5-2s (50-100 candidates)
- Pruning (hierarchical): 1-5s (10-20 constraints selected)
- **Total: 2-7s**

For a layout with 50 views, 5 examples:
- Instantiation: 1-2s (500-1000 templates)
- Learning: 10-20s (500-1000 candidates)
- Pruning (hierarchical): 10-30s (50-100 constraints selected)
- **Total: 20-50s**

Baseline pruner would take minutes to hours for 50 views.

---

## Related Files

### Dependencies (Pipfile)
Key dependencies:
- **Solvers**: `z3-solver`, `kiwisolver`
- **Numeric**: `sympy`, `numpy`, `scipy`, `statsmodels`
- **Logic**: `pyswip` (optional, for Prolog instantiator)
- **Web**: `selenium` (scraping), `starlette` + `uvicorn` (API server)
- **Utils**: `click` (CLI), `jinja2` (templates), `intervaltree` (visibility)

### Setup Files
- `setup.py` - Package metadata
- `setup.cfg` - Package configuration
- `MANIFEST.in` - Include non-Python files in distribution
- `mypy.ini` - Type checking configuration

### Type Stubs (stubs/)
- `stopit.pyi` - Type hints for stopit library
- `sympy/*.pyi` - Type hints for sympy

---

## Summary

The Mockdown codebase is a sophisticated implementation of constraint-based layout synthesis. It follows a clean, modular architecture:

1. **Model** - Generic data structures for layouts
2. **Constraint** - Type-safe constraint representations
3. **Instantiation** - Efficient template generation with visibility pruning
4. **Learning** - Robust Bayesian parameter inference
5. **Pruning** - Scalable hierarchical MaxSMT selection
6. **Integration** - Clean interfaces to Z3 and Kiwi solvers

Key strengths:
- **Modular**: Pluggable algorithms (strategy pattern)
- **Type-safe**: Extensive use of protocols and generics
- **Performant**: Vectorized operations, hierarchical decomposition
- **Robust**: Noise-tolerant learning, visibility graph pruning
- **Extensible**: Clear extension points for new constraint kinds

The implementation closely follows the paper's algorithms while adding practical enhancements:
- NumPy-based instantiation (faster than Prolog)
- Hierarchical pruning decomposition (scalability)
- Comprehensive type system (correctness)
- Multiple output formats (JSON, visualization)

This codebase serves as both a research artifact and a practical tool for layout synthesis.

