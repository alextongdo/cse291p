# Hierarchical Constraint Pruning with MaxSMT

## Overview

The **hierarchical pruning stage** is the final step in the Mockdown constraint inference pipeline and represents its **core innovation**. After Bayesian learning produces many candidate constraints (potentially hundreds), hierarchical pruning selects the "best" subset by:

1. **Decomposing the problem by hierarchy level** - solving parent-child relationships independently
2. **Satisfying layout axioms** (width = right - left, etc.) at each level
3. **Maximizing constraint scores** from Bayesian learning
4. **Generalizing across multiple conformances** (different test sizes)
5. **Inferring child bounds** from parent solutions to enable recursive decomposition

This is formulated as a **Maximum Satisfiability (MaxSMT)** problem using Z3, solved **level-by-level** rather than all at once.

---

## Inputs and Outputs

### Inputs
```python
def prune(
    candidates: List[ConstraintCandidate],  # From Bayesian learning
    examples: List[View],                    # Original training examples
    bounds: ISizeBounds,                     # Optional size bounds
    unambig: bool                            # Whether to enforce unambiguous layouts
) -> Tuple[
    List[LinearConstraint],                  # Selected constraints
    Dict[str, Fraction],                     # Min anchor values (for validation)
    Dict[str, Fraction]                      # Max anchor values (for validation)
]
```

### `ConstraintCandidate` Structure
From the learning stage, each candidate contains:
```python
@dataclass
class ConstraintCandidate:
    constraint: LinearConstraint  # e.g., child.left = 1 * parent.left + 10
    score: float                   # Posterior probability from Bayesian learning
```

### `ISizeBounds` Structure
Optional bounds to test layout generalization:
```python
class ISizeBounds(TypedDict):
    min_w: Optional[Fraction]  # Minimum width to test
    min_h: Optional[Fraction]  # Minimum height to test
    max_w: Optional[Fraction]  # Maximum width to test
    max_h: Optional[Fraction]  # Maximum height to test
    min_x: Optional[Fraction]  # Minimum x position
    min_y: Optional[Fraction]  # Minimum y position
    max_x: Optional[Fraction]  # Maximum x position
    max_y: Optional[Fraction]  # Maximum y position
```

---

## Key Concepts

### 1. **Conformance**
A **conformance** is a specific test size/position for validating layouts:
```python
@dataclass(frozen=True)
class Conformance:
    width: Fraction   # Root width
    height: Fraction  # Root height
    x: Fraction       # Root left position
    y: Fraction       # Root top position
```

The pruner generates a **range of conformances** (typically 5-10) spanning from min to max bounds:
```python
conformances = conformance_range(min_conf, max_conf, scale=5)
# Example: [(800, 600, 0, 0), (850, 650, 0, 0), (900, 700, 0, 0), ...]
```

### 2. **Dimension Separation**
Constraints are separated into **horizontal** (x) and **vertical** (y) dimensions:
- **Horizontal**: left, right, width, center_x
- **Vertical**: top, bottom, height, center_y

Each dimension is solved **independently** with its own Z3 solver.

### 3. **Layout Axioms**
For each view and each conformance, the solver enforces:
```python
# Size axioms
width == right - left
height == bottom - top

# Centering axioms
center_x == (left + right) / 2
center_y == (top + bottom) / 2

# Non-negativity
left >= 0, right >= 0, top >= 0, bottom >= 0
width >= 0, height >= 0
```

### 4. **MaxSMT Formulation**
Each constraint candidate becomes a **boolean variable** with a **soft weight**:

```python
# For each constraint candidate
cvar = z3.Bool(f"constr_var{i}")
solver.add_soft(cvar, weight=bias[constraint])  # Soft constraint

# If selected, constraint must hold across all conformances
for conf_idx in conformances:
    solver.add(z3.Implies(cvar, constraint_to_z3_expr(constraint, conf_idx)))
```

The solver **maximizes** the sum of weights of selected constraints.

---

## Hierarchical Pruning Algorithm

The key innovation is **level-by-level decomposition**: instead of solving all constraints simultaneously, we solve each parent-child relationship independently, then recurse.

### High-Level Algorithm

```python
def hierarchical_prune(candidates, examples, root_bounds):
    """
    Main hierarchical pruning algorithm.
    
    Returns: List of selected constraints
    """
    worklist = [(root, examples, root_bounds)]
    output_constraints = []
    
    while worklist:
        # 1. Pop next level to solve
        focus_view, focus_examples, bounds = worklist.pop()
        
        # 2. Filter to relevant constraints (only parent-child at this level)
        relevant = filter_relevant_constraints(focus_view, candidates)
        
        # 3. Solve MaxSMT for this level
        selected, child_bounds = solve_level(
            focus_view, focus_examples, relevant, bounds
        )
        
        output_constraints.extend(selected)
        
        # 4. Add children to worklist with inferred bounds
        for child in focus_view.children:
            child_examples = [ex.find_view(child.name) for ex in focus_examples]
            worklist.append((child, child_examples, child_bounds[child.name]))
    
    return output_constraints
```

### Step 1: Filter Relevant Constraints

For each level (parent + its immediate children), we only consider constraints where:
- **y anchor** belongs to a child AND **x anchor** (if exists) belongs to parent or sibling
- OR **y anchor** belongs to a child and it's a constant (no x anchor)

```python
def filter_relevant_constraints(focus: View, candidates: List[ConstraintCandidate]) -> List[ConstraintCandidate]:
    """
    Filter constraints relevant to this parent-child level.
    
    A constraint is relevant if:
    - y is a child's anchor
    - x is parent's anchor, or sibling's anchor, or None (constant)
    """
    child_names = {child.name for child in focus.children}
    relevant = []
    
    for cand in candidates:
        y_view = cand.constraint.y.view.name
        
        # y must be a child
        if y_view not in child_names:
            continue
        
        # x can be parent, sibling, or None
        if cand.constraint.x is None:
            # Constant constraint (e.g., child.width = 50)
            relevant.append(cand)
        else:
            x_view = cand.constraint.x.view.name
            if x_view == focus.name or x_view in child_names:
                # Parent-child or sibling-sibling constraint
                relevant.append(cand)
    
    return relevant
```

### Step 2: Solve One Level with MaxSMT

For each level, we solve a MaxSMT problem over the relevant constraints:

```python
def solve_level(focus: View, examples: List[View], 
                candidates: List[ConstraintCandidate], 
                parent_bounds: Conformance) -> Tuple[List[LinearConstraint], Dict[str, Conformance]]:
    """
    Solve MaxSMT for one level of the hierarchy.
    
    Returns:
        selected_constraints: Chosen constraints for this level
        child_bounds: Inferred min/max bounds for each child
    """
    # Create conformance range for testing
    min_conf, max_conf = compute_conformances(examples, parent_bounds)
    conformances = conformance_range(min_conf, max_conf, scale=5)
    
    # Separate by dimension
    x_candidates = [c for c in candidates if is_horizontal(c.constraint)]
    y_candidates = [c for c in candidates if is_vertical(c.constraint)]
    
    # Solve each dimension independently
    x_selected, x_bounds = solve_dimension(
        focus, examples, x_candidates, conformances, x_dim=True
    )
    y_selected, y_bounds = solve_dimension(
        focus, examples, y_candidates, conformances, x_dim=False
    )
    
    # Merge child bounds
    child_bounds = {}
    for child in focus.children:
        child_bounds[child.name] = Conformance(
            width=x_bounds[f"{child.name}.width"],
            height=y_bounds[f"{child.name}.height"],
            x=x_bounds[f"{child.name}.left"],
            y=y_bounds[f"{child.name}.top"]
        )
    
    return x_selected + y_selected, child_bounds
```

### Step 3: Solve One Dimension with MaxSMT

For each dimension (x or y), we formulate and solve a MaxSMT problem:

```python
def solve_dimension(focus: View, examples: List[View],
                   candidates: List[ConstraintCandidate],
                   conformances: List[Conformance],
                   x_dim: bool) -> Tuple[List[LinearConstraint], Dict[str, Fraction]]:
    """
    Solve MaxSMT for one dimension (x or y).
    
    Returns:
        selected_constraints: Chosen constraints
        anchor_bounds: Min/max values for each anchor (for inferring child bounds)
    """
    solver = z3.Optimize()
    names_map = {}
    
    # Normalize scores to weights
    scores = {c.constraint: c.score for c in candidates}
    min_score = min(scores.values()) if scores else 1.0
    weights = {c: int(max(s / min_score, 1e-9) * 1000) for c, s in scores.items()}
    
    # Add constraint variables as soft constraints
    for i, cand in enumerate(candidates):
        cvar = z3.Bool(f"c{i}")
        solver.add_soft(cvar, weights[cand.constraint])
        names_map[f"c{i}"] = cand.constraint
    
    # Add hard constraints for each conformance
    targets = [focus] + list(focus.children)
    for conf_idx, conf in enumerate(conformances):
        # Add layout axioms
        add_layout_axioms(solver, targets, conf, conf_idx, x_dim)
        
        # If constraint selected, must hold for this conformance
        for i, cand in enumerate(candidates):
            cvar = z3.Bool(f"c{i}")
            expr = constraint_to_z3_expr(cand.constraint, conf_idx)
            solver.add(z3.Implies(cvar, expr))
    
    # Solve MaxSMT
    if solver.check() != z3.sat:
        return [], {}
    
    model = solver.model()
    selected = [names_map[v.name()] for v in model.decls()
               if v.name() in names_map and z3.is_true(model[v])]
    
    # Extract anchor bounds (min from first conformance, max from last)
    anchor_bounds = extract_anchor_values(model, targets, conformances, x_dim)
    
    return selected, anchor_bounds
```

### Step 4: Infer Child Bounds

After solving a level, we extract the min/max values for each child's anchors to use as bounds for the next level:

```python
def extract_anchor_values(model: z3.ModelRef, views: List[View],
                         conformances: List[Conformance],
                         x_dim: bool) -> Dict[str, Fraction]:
    """
    Extract min/max anchor values from the Z3 model.
    
    For each child anchor, we get its value at the first (min) and last (max)
    conformance to establish bounds for the child's subproblem.
    """
    bounds = {}
    
    for view in views:
        if x_dim:
            anchors = [
                (view, "width"),
                (view, "left"),
                (view, "right"),
                (view, "center_x")
            ]
        else:
            anchors = [
                (view, "height"),
                (view, "top"),
                (view, "bottom"),
                (view, "center_y")
            ]
        
        for view_obj, anchor_type in anchors:
            # Get value at min conformance (index 0)
            min_var = anchor_to_z3_var(Anchor(view_obj, anchor_type), 0)
            min_val = model.eval(min_var, model_completion=True)
            
            # Get value at max conformance (last index)
            max_idx = len(conformances) - 1
            max_var = anchor_to_z3_var(Anchor(view_obj, anchor_type), max_idx)
            max_val = model.eval(max_var, model_completion=True)
            
            # Store both (we'll use these to create child Conformances)
            key = f"{view_obj.name}.{anchor_type}"
            bounds[key] = (to_fraction(min_val), to_fraction(max_val))
    
    return bounds
```

### Why Hierarchical Decomposition Works

**Key Insight**: Layout problems are naturally hierarchical. A parent's layout typically doesn't depend on its grandchildren's details, only on immediate children.

**Benefits**:
1. **Scalability**: Instead of one problem with N views → N subproblems with ~2-5 views each
2. **Locality**: Only considers relevant constraints at each level
3. **Tight bounds**: Child bounds are inferred from actual parent solution, not just examples
4. **Parallelizable**: Different branches of the hierarchy can be solved independently

**Example**: For a layout with 10 views (1 root + 3 children + 6 grandchildren):
- **Without decomposition**: One problem with ~100-200 constraints
- **With decomposition**: 
  - Level 1: 1 problem with ~20-40 constraints (root + 3 children)
  - Level 2: 3 problems with ~10-15 constraints each (child + grandchildren)
  - Total: 4 smaller problems that are much faster to solve

---

## Integration into Your System

### Step 1: Install Dependencies
```bash
pip install z3-solver
```

### Step 2: Define Data Structures in `src/pruning.py`

Add these to match your existing types:

```python
from dataclasses import dataclass
from fractions import Fraction
from typing import List, Dict, Optional, Tuple
from src.types import View, LinearConstraint, Anchor

@dataclass(frozen=True)
class Conformance:
    """A specific test size/position for layout validation."""
    width: Fraction
    height: Fraction
    x: Fraction
    y: Fraction

@dataclass
class ConstraintCandidate:
    """A constraint with its Bayesian posterior score."""
    constraint: LinearConstraint
    score: float
```

### Step 3: Implement Helper Functions

```python
import z3
from fractions import Fraction

def conformance_range(min_conf: Conformance, max_conf: Conformance, 
                      scale: int = 5) -> List[Conformance]:
    """Generate evenly-spaced conformances between min and max."""
    if min_conf == max_conf:
        return [min_conf]
    
    diffs = [
        (max_conf.width - min_conf.width) / scale,
        (max_conf.height - min_conf.height) / scale,
        (max_conf.x - min_conf.x) / scale,
        (max_conf.y - min_conf.y) / scale
    ]
    
    return [min_conf] + [
        Conformance(
            min_conf.width + diffs[0] * step,
            min_conf.height + diffs[1] * step,
            min_conf.x + diffs[2] * step,
            min_conf.y + diffs[3] * step
        )
        for step in range(1, scale)
    ] + [max_conf]

def anchor_to_z3_var(anchor: Anchor, conf_idx: int) -> z3.ArithRef:
    """Create Z3 variable for an anchor at a specific conformance."""
    return z3.Real(f"{anchor.view.name}.{anchor.type}_{conf_idx}")

def constraint_to_z3_expr(constraint: LinearConstraint, 
                         conf_idx: int) -> z3.BoolRef:
    """Convert constraint to Z3 expression."""
    y_var = anchor_to_z3_var(constraint.y, conf_idx)
    
    if constraint.x is None:
        # y = b (constant)
        return y_var == float(constraint.b)
    else:
        # y = a * x + b
        x_var = anchor_to_z3_var(constraint.x, conf_idx)
        a_float = float(constraint.a) if constraint.a else 1.0
        b_float = float(constraint.b) if constraint.b else 0.0
        return y_var == a_float * x_var + b_float

def is_horizontal(constraint: LinearConstraint) -> bool:
    """Check if constraint is horizontal (x dimension)."""
    h_types = {"left", "right", "width", "center_x"}
    return constraint.y.type in h_types

def add_layout_axioms(solver: z3.Optimize, views: List[View],
                     conf: Conformance, conf_idx: int, x_dim: bool):
    """Add layout axioms for a specific conformance and dimension."""
    for view in views:
        if x_dim:
            # Horizontal: width = right - left, center_x = (left + right) / 2
            w = anchor_to_z3_var(Anchor(view, "width"), conf_idx)
            l = anchor_to_z3_var(Anchor(view, "left"), conf_idx)
            r = anchor_to_z3_var(Anchor(view, "right"), conf_idx)
            cx = anchor_to_z3_var(Anchor(view, "center_x"), conf_idx)
            
            solver.add(w == r - l)
            solver.add(cx == (l + r) / 2)
            solver.add(w >= 0, l >= 0, r >= 0)
        else:
            # Vertical: height = bottom - top, center_y = (top + bottom) / 2
            h = anchor_to_z3_var(Anchor(view, "height"), conf_idx)
            t = anchor_to_z3_var(Anchor(view, "top"), conf_idx)
            b = anchor_to_z3_var(Anchor(view, "bottom"), conf_idx)
            cy = anchor_to_z3_var(Anchor(view, "center_y"), conf_idx)
            
            solver.add(h == b - t)
            solver.add(cy == (t + b) / 2)
            solver.add(h >= 0, t >= 0, b >= 0)

def to_fraction(z3_val) -> Fraction:
    """Convert Z3 numeric value to Fraction."""
    if hasattr(z3_val, 'as_fraction'):
        return z3_val.as_fraction()
    else:
        # Handle integer/real values
        return Fraction(str(z3_val))
```

### Step 4: Implement Hierarchical Pruner

```python
class HierarchicalPruner:
    """
    Hierarchical constraint pruner using MaxSMT.
    
    The key innovation: solve each level of the view hierarchy independently,
    inferring child bounds from parent solutions.
    """
    
    def __init__(self, examples: List[View]):
        self.examples = examples
        self.root = examples[0]
        
        # Compute initial bounds from examples
        widths = [Fraction(ex.width) for ex in examples]
        heights = [Fraction(ex.height) for ex in examples]
        
        self.root_min_conf = Conformance(
            min(widths), min(heights),
            Fraction(0), Fraction(0)
        )
        self.root_max_conf = Conformance(
            max(widths), max(heights),
            Fraction(0), Fraction(0)
        )
    
    def __call__(self, candidates: List[ConstraintCandidate]) -> List[LinearConstraint]:
        """Main entry point: prune candidates to selected set."""
        
        worklist = [(self.root, self.examples, self.root_min_conf, self.root_max_conf)]
        output_constraints = []
        
        while worklist:
            focus, focus_examples, min_conf, max_conf = worklist.pop()
            
            # Filter to relevant constraints for this level
            relevant = self._filter_relevant(focus, candidates)
            
            if not relevant:
                continue
            
            # Solve this level
            selected, child_bounds = self._solve_level(
                focus, focus_examples, relevant, min_conf, max_conf
            )
            
            output_constraints.extend(selected)
            
            # Add children to worklist
            for child in focus.children:
                if child.name in child_bounds:
                    child_examples = [
                        self._find_view_in_example(child.name, ex) 
                        for ex in focus_examples
                    ]
                    child_min, child_max = child_bounds[child.name]
                    worklist.append((child, child_examples, child_min, child_max))
        
        return output_constraints
    
    def _filter_relevant(self, focus: View, 
                        candidates: List[ConstraintCandidate]) -> List[ConstraintCandidate]:
        """Filter constraints relevant to this parent-child level."""
        child_names = {child.name for child in focus.children}
        relevant = []
        
        for cand in candidates:
            y_view = cand.constraint.y.view.name
            
            # y must be a child
            if y_view not in child_names:
                continue
            
            # x can be parent, sibling, or None
            if cand.constraint.x is None:
                relevant.append(cand)
            else:
                x_view = cand.constraint.x.view.name
                if x_view == focus.name or x_view in child_names:
                    relevant.append(cand)
        
        return relevant
    
    def _solve_level(self, focus: View, examples: List[View],
                    candidates: List[ConstraintCandidate],
                    min_conf: Conformance, max_conf: Conformance
                    ) -> Tuple[List[LinearConstraint], Dict[str, Tuple[Conformance, Conformance]]]:
        """Solve MaxSMT for one level."""
        
        conformances = conformance_range(min_conf, max_conf, scale=5)
        
        # Separate by dimension
        x_candidates = [c for c in candidates if is_horizontal(c.constraint)]
        y_candidates = [c for c in candidates if not is_horizontal(c.constraint)]
        
        # Solve each dimension
        x_selected, x_bounds = self._solve_dimension(
            focus, x_candidates, conformances, x_dim=True
        )
        y_selected, y_bounds = self._solve_dimension(
            focus, y_candidates, conformances, x_dim=False
        )
        
        # Merge child bounds
        child_bounds = {}
        for child in focus.children:
            child_min = Conformance(
                width=x_bounds[f"{child.name}.width"][0],
                height=y_bounds[f"{child.name}.height"][0],
                x=x_bounds[f"{child.name}.left"][0],
                y=y_bounds[f"{child.name}.top"][0]
            )
            child_max = Conformance(
                width=x_bounds[f"{child.name}.width"][1],
                height=y_bounds[f"{child.name}.height"][1],
                x=x_bounds[f"{child.name}.left"][1],
                y=y_bounds[f"{child.name}.top"][1]
            )
            child_bounds[child.name] = (child_min, child_max)
        
        return x_selected + y_selected, child_bounds
    
    def _solve_dimension(self, focus: View,
                        candidates: List[ConstraintCandidate],
                        conformances: List[Conformance],
                        x_dim: bool) -> Tuple[List[LinearConstraint], Dict[str, Tuple[Fraction, Fraction]]]:
        """Solve MaxSMT for one dimension."""
        
        if not candidates:
            return [], {}
        
        solver = z3.Optimize()
        names_map = {}
        
        # Normalize scores to weights
        scores = {c.constraint: c.score for c in candidates}
        min_score = min(scores.values())
        weights = {c: int(max(s / min_score, 1e-9) * 1000) for c, s in scores.items()}
        
        # Add constraint variables as soft constraints
        for i, cand in enumerate(candidates):
            cvar = z3.Bool(f"c{i}")
            solver.add_soft(cvar, weights[cand.constraint])
            names_map[f"c{i}"] = cand.constraint
        
        # Add hard constraints for each conformance
        targets = [focus] + list(focus.children)
        for conf_idx, conf in enumerate(conformances):
            # Add layout axioms
            add_layout_axioms(solver, targets, conf, conf_idx, x_dim)
            
            # Fix parent dimensions
            if x_dim:
                w = anchor_to_z3_var(Anchor(focus, "width"), conf_idx)
                l = anchor_to_z3_var(Anchor(focus, "left"), conf_idx)
                solver.add(w == float(conf.width))
                solver.add(l == float(conf.x))
            else:
                h = anchor_to_z3_var(Anchor(focus, "height"), conf_idx)
                t = anchor_to_z3_var(Anchor(focus, "top"), conf_idx)
                solver.add(h == float(conf.height))
                solver.add(t == float(conf.y))
            
            # If constraint selected, must hold for this conformance
            for i, cand in enumerate(candidates):
                cvar = z3.Bool(f"c{i}")
                expr = constraint_to_z3_expr(cand.constraint, conf_idx)
                solver.add(z3.Implies(cvar, expr))
        
        # Solve MaxSMT
        if solver.check() != z3.sat:
            print(f"WARNING: No solution found for {focus.name} ({'x' if x_dim else 'y'} dim)")
            return [], {}
        
        model = solver.model()
        selected = [names_map[v.name()] for v in model.decls()
                   if v.name() in names_map and z3.is_true(model[v])]
        
        # Extract anchor bounds
        anchor_bounds = self._extract_bounds(model, targets, conformances, x_dim)
        
        return selected, anchor_bounds
    
    def _extract_bounds(self, model: z3.ModelRef, views: List[View],
                       conformances: List[Conformance],
                       x_dim: bool) -> Dict[str, Tuple[Fraction, Fraction]]:
        """Extract min/max anchor values from Z3 model."""
        bounds = {}
        
        anchor_types = ["width", "left", "right", "center_x"] if x_dim else \
                      ["height", "top", "bottom", "center_y"]
        
        for view in views:
            for anchor_type in anchor_types:
                # Get value at min conformance (index 0)
                min_var = anchor_to_z3_var(Anchor(view, anchor_type), 0)
                min_val = model.eval(min_var, model_completion=True)
                
                # Get value at max conformance (last index)
                max_idx = len(conformances) - 1
                max_var = anchor_to_z3_var(Anchor(view, anchor_type), max_idx)
                max_val = model.eval(max_var, model_completion=True)
                
                key = f"{view.name}.{anchor_type}"
                bounds[key] = (to_fraction(min_val), to_fraction(max_val))
        
        return bounds
    
    def _find_view_in_example(self, view_name: str, example: View) -> View:
        """Find a view by name in an example hierarchy."""
        for view in example._flattened_views_in_subtree:
            if view.name == view_name:
                return view
        raise ValueError(f"View {view_name} not found in example")
```

### Step 5: Usage

```python
# After template instantiation and Bayesian learning
from src.instantiation import template_instantiation
from src.learning import bayesian_learning
from src.pruning import HierarchicalPruner

# 1. Load examples
examples = [load_example(path) for path in example_paths]

# 2. Instantiate templates
templates = template_instantiation(examples)

# 3. Learn parameters
candidates = bayesian_learning(templates, examples)

# 4. Hierarchical pruning
pruner = HierarchicalPruner(examples)
selected_constraints = pruner(candidates)

print(f"Selected {len(selected_constraints)} / {len(candidates)} constraints")
for constraint in selected_constraints:
    print(f"  {constraint}")
```

---

## Configuration Parameters

### `conformance_scale: int` (default: 5)
Number of test sizes to validate layouts across between min and max bounds.

**Trade-off**: 
- More conformances = better generalization but slower solving
- Fewer conformances = faster but may miss edge cases

**Typical values**: 3-7 conformances

### `weight_normalization_factor: int` (default: 1000)
Multiplier to convert floating-point scores to integer weights for Z3.

**Why needed**: Z3's MaxSMT solver works with integer weights. Multiply by a large factor to preserve precision.

**Typical values**: 1000-10000

---

## Debugging

### SMT Formula Export
```python
# Export SMT2 format for inspection
solver = z3.Optimize()
# ... add constraints ...
with open("debug.smt2", "w") as f:
    f.write(solver.sexpr())
```

### Visualization
```python
# Check which constraints were pruned
pruned = set(c.constraint for c in candidates) - set(selected)
print(f"Pruned {len(pruned)} constraints:")
for c in pruned:
    print(f"  {c} (score: {scores[c]:.3f})")
```

### Validation
```python
# Verify selected constraints are satisfiable
from your_kiwi_integration import evaluate_constraints

try:
    result = evaluate_constraints(
        view=examples[0],
        constraints=selected_constraints,
        top_rect=(0, 0, 800, 600)
    )
    print("✓ Constraints are satisfiable")
except Exception as e:
    print(f"✗ Constraints are unsatisfiable: {e}")
```

---

## Comparison with Original Mockdown

### Your Implementation vs Mockdown

| Feature | Your System | Mockdown |
|---------|-------------|----------|
| Constraint Types | `LinearConstraint(y, x, a, b)` | `LinearConstraint`, `ConstantConstraint` |
| Solver | Z3 Optimize | Z3 Optimize |
| Dimension Separation | ✓ Same (x and y independent) | ✓ Same |
| MaxSMT Formulation | ✓ Same (soft constraints) | ✓ Same |
| Hierarchical Decomposition | ✓ Level-by-level | ✓ Level-by-level |
| Conformance Range | ✓ Same (min to max) | ✓ Same |
| Child Bound Inference | ✓ From Z3 model | ✓ From Z3 model |

### Simplified Assumptions for Your System

The documentation above follows the core Mockdown algorithm but makes these simplifications:

1. **No Unambiguous Check**: Mockdown has an optional counterexample-guided synthesis step to ensure deterministic layouts. This is complex and can be added later if needed.

2. **Fixed Conformance Scale**: Use 5 conformances (min, 3 intermediate points, max). Mockdown allows this to be configurable.

3. **Simple Weight Normalization**: Use `int(score / min_score * 1000)` for Z3 weights. Mockdown has additional logic for handling very small scores.

4. **No Size Bound Override**: Mockdown allows manually specifying min/max bounds. Your implementation computes them from examples, which is simpler and usually sufficient.

---

## Summary

The **hierarchical pruning stage** is the key innovation of Mockdown and works as follows:

1. **Input**: Hundreds of candidate constraints from Bayesian learning, each with a score
2. **Decomposition**: Process the view hierarchy level-by-level (parent + immediate children)
3. **Filtering**: At each level, consider only constraints between parent and children
4. **MaxSMT Solving**: 
   - Solve x and y dimensions independently
   - Maximize sum of constraint scores
   - Subject to layout axioms (width = right - left, etc.)
   - Test across multiple conformances (different sizes)
5. **Child Bound Inference**: Extract min/max anchor values from solution to constrain child subproblems
6. **Recursion**: Add children to worklist with inferred bounds and repeat
7. **Output**: ~10-30 selected constraints that form a complete, satisfiable layout specification

### Why This Matters

**Scalability**: Instead of solving one giant problem with N views and M constraints, we solve O(N) smaller problems with O(M/N) constraints each. This makes the approach tractable for large hierarchies.

**Locality**: Each level only reasons about immediate parent-child relationships, matching the natural structure of UI layouts.

**Generalization**: Testing across multiple conformances ensures the selected constraints work not just for the training examples but for a range of sizes.

This is the most complex stage of the Mockdown pipeline but crucial for producing **concise, general, and correct** layout constraints from noisy, redundant learned candidates.

