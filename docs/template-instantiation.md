# Template Instantiation - Local Inference

## Confirmation: Separation from Parameter Learning

**Yes, template instantiation is completely separate from parameter learning in the Mockdown codebase.**

Evidence from `run.py` (lines 152-198):
```python
# Step 2: Instantiate Templates
instantiator = instantiator_factory(examples)
templates = instantiator.instantiate()  # Returns templates with sample_count=0

# Can return early with just templates (no learning)
if options.get('debug_instantiation'):
    return {'constraints': [tpl.to_dict() for tpl in templates], 'axioms': []}

# Step 3: Learn Constants (separate step, uses templates as input)
learning = learning_factory(samples=examples, templates=templates, config=learning_config)
candidates = list(flatten(learning.learn()))
```

**Key characteristics of templates:**
- Have `sample_count=0` (line 30, 79 in `constraint/constraint.py`)
- Have unknown parameters marked as defaults: `a=sym.Rational(1)`, `b=sym.Rational(0)`
- Implement `subst(a, b, sample_count)` method to be filled in by learning
- Are constraint "sketches" - they specify the form `y = a·x + b` but not the values of `a` and `b`

**Interface**:
```python
class IConstraintInstantiator(Protocol[NT]):
    def __init__(self, examples: Sequence[IView[NT]]): ...
    def instantiate(self) -> Sequence[IConstraint]: ...
```

Input: Multiple layout examples (same structure, different screen sizes)
Output: Constraint templates (form specified, parameters unknown)

---

## Overview

Template instantiation (also called "local inference" in the paper) is the first phase of the Mockdown pipeline. It generates a set of candidate constraint templates by:

1. Computing which UI elements can "see" each other (visibility graph)
2. Identifying valid anchor pairs based on geometric and semantic rules
3. Generating constraint templates for each valid pair

The output is a set of constraint **sketches** where the form is determined (`y = a·x + b`) but the parameters `a` and `b` are unknown (to be learned in the next phase).

---

## Input Format

### Hierarchical Layout JSON

**Example Input** (multiple examples required):
```json
{
  "examples": [
    {
      "name": "root",
      "rect": [0, 0, 800, 600],
      "children": [
        {"name": "header", "rect": [0, 0, 800, 80], "children": []},
        {"name": "sidebar", "rect": [0, 80, 200, 600], "children": []},
        {"name": "main", "rect": [200, 80, 800, 600], "children": []}
      ]
    },
    {
      "name": "root",
      "rect": [0, 0, 1200, 800],
      "children": [
        {"name": "header", "rect": [0, 0, 1200, 80], "children": []},
        {"name": "sidebar", "rect": [0, 80, 200, 800], "children": []},
        {"name": "main", "rect": [200, 80, 1200, 800], "children": []}
      ]
    }
  ]
}
```

**Loaded as View hierarchy**:
```python
View(
    name="root",
    rect=Rect(left=0, top=0, right=800, bottom=600),
    children=[
        View(name="header", rect=Rect(...)),
        View(name="sidebar", rect=Rect(...)),
        View(name="main", rect=Rect(...))
    ]
)
```

**Anchors extracted** (8 per view):
- Position: `left`, `top`, `right`, `bottom`, `center_x`, `center_y`
- Size: `width`, `height`

Example: `header.left`, `sidebar.width`, `main.center_x`, etc.

---

## Output Format

### Constraint Templates

**Example Output**:
```python
[
    LinearConstraint(
        kind=ConstraintKind.SIZE_CONSTANT,
        y_id=AnchorID("header", Attribute.HEIGHT),
        x_id=None,
        a=Rational(0),      # Fixed to 0 for constant form
        b=Rational(0),      # UNKNOWN - to be learned
        op=operator.eq,
        sample_count=0      # Indicates this is a template
    ),
    
    LinearConstraint(
        kind=ConstraintKind.SIZE_RATIO,
        y_id=AnchorID("sidebar", Attribute.WIDTH),
        x_id=AnchorID("root", Attribute.WIDTH),
        a=Rational(1),      # UNKNOWN - to be learned
        b=Rational(0),      # Fixed to 0 for ratio form
        op=operator.eq,
        sample_count=0
    ),
    
    LinearConstraint(
        kind=ConstraintKind.POS_LTRB_OFFSET,
        y_id=AnchorID("main", Attribute.TOP),
        x_id=AnchorID("header", Attribute.BOTTOM),
        a=Rational(1),      # Fixed to 1 for offset form
        b=Rational(0),      # UNKNOWN - to be learned
        op=operator.eq,
        sample_count=0
    ),
    
    # ... many more templates
]
```

**Key fields**:
- `kind`: Determines the constraint form and which parameters are unknown
- `y_id`, `x_id`: Which anchors are involved
- `sample_count=0`: Marker that this is a template (not learned)
- Default parameter values: Will be replaced by learning

---

## Algorithm Steps

### Step 0: Data Structure Setup

**Extract all anchors** from the first example (all examples must be isomorphic):

```python
# For each view in hierarchy, extract 8 anchors
anchors = []
for view in all_views_in_hierarchy:
    anchors.extend([
        view.left_anchor, view.right_anchor,
        view.top_anchor, view.bottom_anchor,
        view.width_anchor, view.height_anchor,
        view.center_x_anchor, view.center_y_anchor
    ])
```

**Create index**: MultiIndex of (view_name, attribute) pairs for efficient querying.

---

### Step 1: Compute Visibility Graph

**Purpose**: Determine which anchor pairs can "see" each other (no intervening UI elements).

**Algorithm** (Sweep-line with Interval Trees):

```python
def visible_pairs(view: IView) -> List[Tuple[Edge, Edge]]:
    # 1. Build interval trees for edges
    x_itree = IntervalTree()  # For horizontal edges (top, bottom)
    y_itree = IntervalTree()  # For vertical edges (left, right)
    
    for child in view.children:
        # Add horizontal edges with their x-intervals
        x_itree.add(child.left, child.right, child.top_edge)
        x_itree.add(child.left, child.right, child.bottom_edge)
        
        # Add vertical edges with their y-intervals
        y_itree.add(child.top, child.bottom, child.left_edge)
        y_itree.add(child.top, child.bottom, child.right_edge)
    
    pairs = []
    
    # 2. Sweep vertical lines through horizontal edges
    for x in all_edge_x_coordinates:
        # Query all horizontal edges at this x-coordinate
        edges_at_x = x_itree.query(x)
        
        # Sort by y-position
        sorted_edges = sorted(edges_at_x, key=lambda e: e.position)
        
        # Add parent edges to ends
        sorted_edges.insert(0, view.top_edge)
        sorted_edges.append(view.bottom_edge)
        
        # Adjacent edges in sorted order are visible
        for edge1, edge2 in zip(sorted_edges, sorted_edges[1:]):
            if edge1.view != edge2.view:
                pairs.append((edge1, edge2))
                # Also add center edges for alignment
                pairs.append((edge1.view.center_y_edge, edge2.view.center_y_edge))
    
    # 3. Sweep horizontal lines through vertical edges (symmetric)
    for y in all_edge_y_coordinates:
        edges_at_y = y_itree.query(y)
        sorted_edges = sorted(edges_at_y, key=lambda e: e.position)
        sorted_edges.insert(0, view.left_edge)
        sorted_edges.append(view.right_edge)
        
        for edge1, edge2 in zip(sorted_edges, sorted_edges[1:]):
            if edge1.view != edge2.view:
                pairs.append((edge1, edge2))
                pairs.append((edge1.view.center_x_edge, edge2.view.center_x_edge))
    
    # 4. Recurse for child hierarchies
    for child in view.children:
        pairs.extend(visible_pairs(child))
    
    return pairs
```

**Visual Example**:
```
+------------------+
|  header          |  ← root.top and header.bottom are visible
+------+-----------+
| side | main      |  ← side.right and main.left are visible
| bar  |           |     header.bottom and side.top are visible
+------+-----------+
```

**Result**: Set of anchor pairs like:
- `(header.bottom, sidebar.top)`
- `(header.bottom, main.top)`
- `(sidebar.right, main.left)`
- `(header.center_y, sidebar.center_y)` (for alignment)

**Purpose of visibility**:
- Prunes unrealistic constraints (e.g., relating far-apart elements)
- Based on intuition: UI elements positioned relative to nearby elements
- Reduces search space from O(N²) to O(N) anchor pairs

---

### Step 2: Build Relationship Matrices

**Create NxN matrices** (N = number of anchors) encoding relationships:

#### 2.1 Attribute Type Matrices

```python
# Vector: is this anchor a size attribute? (width or height)
is_size_vec = [a.attribute.is_size() for a in anchors]
# Result: [0, 0, 0, 0, 1, 1, 0, 0] for (l,t,r,b,w,h,cx,cy)

# Matrix: are both anchors size attributes?
both_size_mat = outer_product(is_size_vec, is_size_vec)
# Result: 1 at (i,j) iff both anchors[i] and anchors[j] are sizes

# Similarly for position attributes
is_pos_vec = [a.attribute.is_position() for a in anchors]
both_pos_mat = outer_product(is_pos_vec, is_pos_vec)
```

#### 2.2 Axis Matrices

```python
# Horizontal attributes: left, right, center_x, width
is_h_vec = [a.attribute.is_horizontal() for a in anchors]
both_h_mat = outer_product(is_h_vec, is_h_vec)

# Vertical attributes: top, bottom, center_y, height
is_v_vec = [a.attribute.is_vertical() for a in anchors]
both_v_mat = outer_product(is_v_vec, is_v_vec)

# Cross-product: horizontal × vertical (for aspect ratios)
hv_mat = outer_product(is_h_vec, is_v_vec)
```

#### 2.3 Attribute Compatibility Matrices

```python
# Same attribute (e.g., both are "left")
same_attr_mat[i][j] = (anchors[i].attribute == anchors[j].attribute)

# Dual pair (e.g., left/right, top/bottom)
dual_attr_mat[i][j] = is_dual_pair(anchors[i].attribute, anchors[j].attribute)
```

#### 2.4 Visibility Matrix

```python
# Convert visibility pairs to matrix
visible_mat[i][j] = (anchors[i].id, anchors[j].id) in visibility_pairs

# Make symmetric
visible_mat |= visible_mat.transpose()
```

#### 2.5 View Relationship Matrices

```python
# Same view (e.g., both anchors from "header")
same_view_mat[i][j] = (anchors[i].view == anchors[j].view)

# Parent-child relationship
# Note: Column is parent of row (not symmetric!)
parent_mat[i][j] = anchors[i].view.is_child_of(anchors[j].view)

# Sibling relationship
sibling_mat[i][j] = anchors[i].view.is_sibling_of(anchors[j].view)
```

#### 2.6 View-Level Visibility Matrices

```python
# Horizontal visibility at view level
# Two views are h-visible if any of their horizontal anchors are visible
h_vis_view_mat = (both_h_mat & visible_mat) \
    .groupby(by_view).any() \
    .groupby(by_view).any()

# Vertical visibility at view level
v_vis_view_mat = (both_v_mat & visible_mat) \
    .groupby(by_view).any() \
    .groupby(by_view).any()
```

**Why matrices?**: Enable vectorized operations to quickly identify valid anchor pairs.

---

### Step 3: Identify Valid Constraint Patterns

Combine matrices using boolean operations to find anchor pairs satisfying constraint validity rules.

#### 3.1 Aspect Ratio Constraints (`width = a · height`)

**Rule**: Same view, both sizes, different axes (horizontal × vertical)

```python
aspect_ratio_mat = same_view_mat & both_size_mat & hv_mat
```

**Example matches**:
- `(header.width, header.height)` ✓
- `(sidebar.width, sidebar.height)` ✓
- `(header.width, sidebar.width)` ✗ (different views)
- `(header.width, header.left)` ✗ (left is not a size)

**Generated templates**:
```python
for (anchor_y, anchor_x) in pairs_where(aspect_ratio_mat):
    yield LinearConstraint(
        kind=ConstraintKind.SIZE_ASPECT_RATIO,
        y_id=anchor_y.id,
        x_id=anchor_x.id,
        a=Rational(1),  # UNKNOWN
        b=Rational(0),  # Fixed
        sample_count=0
    )
```

#### 3.2 Parent-Relative Size Constraints (`child.width = a · parent.width`)

**Rule**: Parent-child, both sizes, same axis

```python
parent_relative_size_mat = parent_mat & both_size_mat & (both_h_mat | both_v_mat)
```

**Example matches**:
- `(sidebar.width, root.width)` ✓ (child size, parent size, both horizontal)
- `(header.height, root.height)` ✓ (child size, parent size, both vertical)
- `(sidebar.width, root.height)` ✗ (different axes)
- `(sidebar.left, root.left)` ✗ (positions, not sizes)

**Generated templates**:
```python
for (anchor_y, anchor_x) in pairs_where(parent_relative_size_mat):
    yield LinearConstraint(
        kind=ConstraintKind.SIZE_RATIO,
        y_id=anchor_y.id,
        x_id=anchor_x.id,
        a=Rational(1),  # UNKNOWN
        b=Rational(0),  # Fixed
        sample_count=0
    )
```

#### 3.3 Sibling-Relative Size Constraints (Commented Out)

**Note**: Lines 139-145 in `numpy/instantiator.py` show this is **commented out** in the actual implementation.

**Original rule**: Siblings, same size attribute, visible, same axis

```python
# NOT USED in current implementation
sibrel_size_h_mat = v_vis_view_mat & both_h_mat & sibling_mat & both_size_mat & same_attr_mat
sibrel_size_v_mat = h_vis_view_mat & both_v_mat & sibling_mat & both_size_mat & same_attr_mat
sibling_relative_size_mat = sibrel_size_h_mat | sibrel_size_v_mat
```

**Why commented out?**: Likely causes over-generation of templates or conflicts with other constraints.

#### 3.4 Absolute Size Constraints (`width = b`)

**Rule**: Any size attribute

```python
absolute_size_vec = is_size_vec
```

**Example matches**:
- `header.height` ✓
- `sidebar.width` ✓
- `main.width` ✓
- `header.left` ✗ (position, not size)

**Generated templates**:
```python
for anchor in anchors_where(absolute_size_vec):
    yield ConstantConstraint(
        kind=ConstraintKind.SIZE_CONSTANT,
        y_id=anchor.id,
        x_id=None,
        a=Rational(0),  # Fixed (no x variable)
        b=Rational(0),  # UNKNOWN
        sample_count=0
    )
```

#### 3.5 Offset Position Constraints (`y = x + b`)

**Rule**: Two cases combined with OR:
1. **Parent-child**: Parent-child, both positions, same attribute, visible
2. **Sibling dual**: Siblings, both positions, dual attributes, visible

```python
# Case 1: Parent-child offset (e.g., child.top = parent.top + b)
offset_pos_pc_mat = parent_mat & both_pos_mat & same_attr_mat & visible_mat

# Case 2: Sibling dual offset (e.g., sidebar.right = main.left + b)
offset_pos_sib_mat = sibling_mat & both_pos_mat & dual_attr_mat & visible_mat

offset_pos_mat = offset_pos_pc_mat | offset_pos_sib_mat
```

**Example matches**:
- `(sidebar.top, header.bottom)` ✓ (sibling, positions, top/bottom are dual, visible)
- `(main.left, sidebar.right)` ✓ (sibling, positions, left/right are dual, visible)
- `(sidebar.left, root.left)` ✓ (parent-child, positions, same attribute, visible)
- `(sidebar.left, main.right)` ✗ (siblings but not dual: left/right not adjacent)

**Generated templates**:
```python
for (anchor_y, anchor_x) in pairs_where(offset_pos_mat):
    yield LinearConstraint(
        kind=ConstraintKind.POS_LTRB_OFFSET,
        y_id=anchor_y.id,
        x_id=anchor_x.id,
        a=Rational(1),  # Fixed
        b=Rational(0),  # UNKNOWN
        sample_count=0
    )
```

#### 3.6 Alignment Position Constraints (`y = x`)

**Rule**: Siblings, same position attribute, visible, same axis

```python
# Horizontal alignment (e.g., both left edges align)
align_h_mat = v_vis_view_mat & both_h_mat & sibling_mat & both_pos_mat & same_attr_mat

# Vertical alignment (e.g., both top edges align)
align_v_mat = h_vis_view_mat & both_v_mat & sibling_mat & both_pos_mat & same_attr_mat

align_pos_mat = align_h_mat | align_v_mat
```

**Example matches**:
- `(sidebar.left, main.left)` if both have same left coordinate ✓
- `(sidebar.top, main.top)` if both have same top coordinate ✓
- `(sidebar.center_x, main.center_x)` ✓ (for centered alignment)

**Note**: These are **combined with offset positions** in the final template generation (line 154):

```python
for (anchor_y, anchor_x) in pairs_where(offset_pos_mat | align_pos_mat):
    yield LinearConstraint(
        kind=ConstraintKind.POS_LTRB_OFFSET,  # Same kind for both!
        y_id=anchor_y.id,
        x_id=anchor_x.id,
        a=Rational(1),
        b=Rational(0),  # Will be 0 for alignment, non-zero for offset
        sample_count=0
    )
```

**Design choice**: Alignment is treated as offset with `b=0` (to be learned). The learning phase will determine if `b≈0` (alignment) or `b≠0` (offset).

---

### Step 4: Generate Constraint Templates

Iterate through valid anchor pairs and create constraint objects:

```python
def gen_templates():
    # 1. Aspect ratios: width = a · height
    for (y_anchor, x_anchor) in pairs_where(aspect_ratio_mat):
        yield ConstraintFactory.create(
            kind=ConstraintKind.SIZE_ASPECT_RATIO,
            y_id=y_anchor.id,
            x_id=x_anchor.id,
            op=operator.eq
        )
    
    # 2. Parent-relative sizes: child.size = a · parent.size
    for (y_anchor, x_anchor) in pairs_where(parent_relative_size_mat):
        yield ConstraintFactory.create(
            kind=ConstraintKind.SIZE_RATIO,
            y_id=y_anchor.id,
            x_id=x_anchor.id,
            op=operator.eq
        )
    
    # 3. Absolute sizes: element.size = b
    for y_anchor in anchors_where(absolute_size_vec):
        yield ConstraintFactory.create(
            kind=ConstraintKind.SIZE_CONSTANT,
            y_id=y_anchor.id,
            op=operator.eq
        )
    
    # 4. Offset/Aligned positions: y = x + b (or y = x if b=0)
    for (y_anchor, x_anchor) in pairs_where(offset_pos_mat | align_pos_mat):
        yield ConstraintFactory.create(
            kind=ConstraintKind.POS_LTRB_OFFSET,
            y_id=y_anchor.id,
            x_id=x_anchor.id,
            op=operator.eq
        )

templates = list(gen_templates())
```

**ConstraintFactory.create()** determines the appropriate constraint class:
- `ConstantConstraint` for constant forms (SIZE_CONSTANT)
- `LinearConstraint` for all others

---

## Constraint Kinds Reference

| Kind | Form | Example | Unknown Params |
|------|------|---------|----------------|
| SIZE_CONSTANT | `y = b` | `header.height = 80` | `b` |
| SIZE_RATIO | `y = a·x` | `sidebar.width = 0.2 · root.width` | `a` |
| SIZE_ASPECT_RATIO | `y = a·x` | `view.width = 1.5 · view.height` | `a` |
| POS_LTRB_OFFSET | `y = x + b` | `main.top = header.bottom + 0` | `b` |
| POS_CENTERING | `y = x` | `child.center_x = parent.center_x` | none (special case of OFFSET with b=0) |

**Note**: POS_CENTERING is not explicitly generated; it emerges when POS_LTRB_OFFSET is learned with `b≈0`.

---

## Implementation Details

### NumPy vs Prolog Implementation

**NumPy Implementation** (`instantiation/numpy/instantiator.py`):
- Uses vectorized matrix operations
- Fast: O(N²) where N = number of anchors
- Default method
- No external dependencies beyond NumPy/Pandas

**Prolog Implementation** (`instantiation/prolog/instantiator.py`):
- Uses SWI-Prolog via PySwip
- Encodes rules declaratively in `logic.pl`
- Slower but more maintainable for complex rules
- Requires SWI-Prolog installation
- Less commonly used

### Optimizations

1. **Visibility Graph**: Reduces O(N²) to O(N) viable pairs
2. **Matrix Operations**: Vectorized operations on all pairs simultaneously
3. **Early Filtering**: Invalid pairs never become constraint objects
4. **Pandas MultiIndex**: Efficient grouping by view for view-level operations

### Typical Output Size

For a layout with 10 views (80 anchors):
- Naive: 80² = 6,400 possible pairs
- After visibility: ~200 visible pairs
- After semantic rules: ~50-100 valid templates

For a layout with 50 views (400 anchors):
- Naive: 400² = 160,000 possible pairs
- After visibility: ~1,000 visible pairs
- After semantic rules: ~500-1000 valid templates

---

## Debugging and Validation

### Debug Output

```bash
# View only visibility graph
mockdown run input.json output.json --debug-visibilities

# View generated templates (no learning)
mockdown run input.json output.json --debug-instantiation
```

### Expected Output

**debug-instantiation output**:
```json
{
  "constraints": [
    {"kind": "size_constant", "y": "header.height", "op": "=", "b": "0"},
    {"kind": "size_ratio", "y": "sidebar.width", "x": "root.width", "op": "=", "a": "1", "b": "0"},
    {"kind": "pos_lrtb_offset", "y": "main.top", "x": "header.bottom", "op": "=", "a": "1", "b": "0"},
    ...
  ]
}
```

Notice `b: "0"` for unknowns - these are default values, not learned yet.

### Validation Checklist

✓ **All views have size constraints**: Each view should have templates for width/height
✓ **Parent-child relationships exist**: Child positions should relate to parent
✓ **Sibling relationships exist**: Adjacent siblings should have offset constraints
✓ **No impossible constraints**: e.g., no constraints between disconnected components
✓ **Count reasonable**: Roughly 5-10 templates per view is typical

### Common Issues

**Too few templates** (<5 per view):
- Visibility graph may be too restrictive
- Examples may not be isomorphic
- Check that examples have same hierarchy structure

**Too many templates** (>20 per view):
- Visibility graph may be including too many pairs
- May need additional semantic rules
- Not necessarily wrong, but learning/pruning will be slower

**Missing expected constraints**:
- Check visibility: Are the elements visible to each other?
- Check semantic rules: Do both anchors satisfy the rule?
- Print intermediate matrices to debug

---

## Example Walkthrough

### Input

Two examples of a simple layout:

**Example 1** (800×600):
```
+------------------+
|  header (800×80) |
+------+-----------+
| side | main      |
| bar  | (600×520) |
| (200 |           |
| ×520)|           |
+------+-----------+
```

**Example 2** (1200×800):
```
+---------------------------+
|  header (1200×80)         |
+------+--------------------+
| side | main               |
| bar  | (1000×720)         |
| (200 |                    |
| ×720)|                    |
+------+--------------------+
```

### Step-by-Step Execution

#### Step 0: Extract Anchors

```python
anchors = [
    Anchor(root, LEFT),     # root.left = 0
    Anchor(root, TOP),      # root.top = 0
    Anchor(root, RIGHT),    # root.right = 800 (ex1) / 1200 (ex2)
    Anchor(root, BOTTOM),   # root.bottom = 600 (ex1) / 800 (ex2)
    Anchor(root, WIDTH),    # root.width = 800 / 1200
    Anchor(root, HEIGHT),   # root.height = 600 / 800
    
    Anchor(header, LEFT),   # header.left = 0
    Anchor(header, TOP),    # header.top = 0
    Anchor(header, RIGHT),  # header.right = 800 / 1200
    Anchor(header, BOTTOM), # header.bottom = 80
    Anchor(header, WIDTH),  # header.width = 800 / 1200
    Anchor(header, HEIGHT), # header.height = 80
    
    Anchor(sidebar, LEFT),  # sidebar.left = 0
    Anchor(sidebar, TOP),   # sidebar.top = 80
    Anchor(sidebar, RIGHT), # sidebar.right = 200
    Anchor(sidebar, BOTTOM),# sidebar.bottom = 600 / 800
    Anchor(sidebar, WIDTH), # sidebar.width = 200
    Anchor(sidebar, HEIGHT),# sidebar.height = 520 / 720
    
    Anchor(main, LEFT),     # main.left = 200
    Anchor(main, TOP),      # main.top = 80
    Anchor(main, RIGHT),    # main.right = 800 / 1200
    Anchor(main, BOTTOM),   # main.bottom = 600 / 800
    Anchor(main, WIDTH),    # main.width = 600 / 1000
    Anchor(main, HEIGHT),   # main.height = 520 / 720
    # ... center_x, center_y for each view
]
```

Total: 4 views × 8 anchors = 32 anchors

#### Step 1: Compute Visibility

**Sweeping vertical lines** (at x = 0, 200, 800/1200):

At x=0:
- Edges: root.top(y=0), header.top(y=0), header.bottom(y=80), sidebar.top(y=80), sidebar.bottom(y=600/800), root.bottom(y=600/800)
- Adjacent: (header.bottom, sidebar.top) ✓

At x=200:
- Edges: root.top, header.top, header.bottom, sidebar.top, main.top, main.bottom, sidebar.bottom, root.bottom
- Adjacent: (header.bottom, sidebar.top) ✓, (header.bottom, main.top) ✓, (sidebar.bottom, root.bottom) ✓, (main.bottom, root.bottom) ✓

**Sweeping horizontal lines** (at y = 0, 80, 600/800):

At y=80:
- Edges: root.left, header.left, sidebar.left, sidebar.right, main.left, main.right, header.right, root.right
- Adjacent: (sidebar.right, main.left) ✓

**Visibility pairs**:
```python
visible_pairs = [
    (header.bottom, sidebar.top),
    (header.bottom, main.top),
    (sidebar.right, main.left),
    # ... plus center edges
]
```

#### Step 2: Build Matrices

**parent_mat** (4×4 at view level):
```
        root  header  sidebar  main
root    0     0       0        0
header  1     0       0        0
sidebar 1     0       0        0
main    1     0       0        0
```

**sibling_mat**:
```
        root  header  sidebar  main
root    0     0       0        0
header  0     0       1        1
sidebar 0     1       0        1
main    0     1       1        0
```

**visible_mat** (32×32, showing relevant pairs):
```
                    header.bottom  sidebar.top  sidebar.right  main.left
header.bottom       0              1            0              1
sidebar.top         1              0            0              0
sidebar.right       0              0            0              1
main.left           1              0            1              0
```

#### Step 3: Identify Patterns

**Aspect ratios** (same_view & both_size & hv):
- `(header.width, header.height)` ✓
- `(sidebar.width, sidebar.height)` ✓
- `(main.width, main.height)` ✓

**Parent-relative sizes** (parent & both_size & same_axis):
- `(header.width, root.width)` ✓
- `(header.height, root.height)` ✓
- `(sidebar.width, root.width)` ✓
- `(sidebar.height, root.height)` ✓
- `(main.width, root.width)` ✓
- `(main.height, root.height)` ✓

**Absolute sizes** (all size anchors):
- `header.width`, `header.height`
- `sidebar.width`, `sidebar.height`
- `main.width`, `main.height`
- `root.width`, `root.height`

**Offset positions** (visible & (parent same attr OR sibling dual)):
- `(sidebar.top, header.bottom)` ✓ (sibling, visible, dual)
- `(main.top, header.bottom)` ✓ (sibling, visible, dual)
- `(main.left, sidebar.right)` ✓ (sibling, visible, dual)
- `(header.left, root.left)` ✓ (parent-child, visible, same)
- `(sidebar.left, root.left)` ✓ (parent-child, visible, same)

#### Step 4: Generate Templates

**Output** (simplified, ~20-30 templates total):
```python
[
    # Aspect ratios
    LinearConstraint(SIZE_ASPECT_RATIO, y=header.width, x=header.height, a=?, b=0),
    LinearConstraint(SIZE_ASPECT_RATIO, y=sidebar.width, x=sidebar.height, a=?, b=0),
    LinearConstraint(SIZE_ASPECT_RATIO, y=main.width, x=main.height, a=?, b=0),
    
    # Parent-relative sizes
    LinearConstraint(SIZE_RATIO, y=header.width, x=root.width, a=?, b=0),
    LinearConstraint(SIZE_RATIO, y=sidebar.width, x=root.width, a=?, b=0),
    LinearConstraint(SIZE_RATIO, y=main.width, x=root.width, a=?, b=0),
    LinearConstraint(SIZE_RATIO, y=header.height, x=root.height, a=?, b=0),
    LinearConstraint(SIZE_RATIO, y=sidebar.height, x=root.height, a=?, b=0),
    LinearConstraint(SIZE_RATIO, y=main.height, x=root.height, a=?, b=0),
    
    # Absolute sizes
    ConstantConstraint(SIZE_CONSTANT, y=header.width, b=?),
    ConstantConstraint(SIZE_CONSTANT, y=header.height, b=?),
    ConstantConstraint(SIZE_CONSTANT, y=sidebar.width, b=?),
    # ... etc for all size anchors
    
    # Offset positions
    LinearConstraint(POS_LTRB_OFFSET, y=sidebar.top, x=header.bottom, a=1, b=?),
    LinearConstraint(POS_LTRB_OFFSET, y=main.top, x=header.bottom, a=1, b=?),
    LinearConstraint(POS_LTRB_OFFSET, y=main.left, x=sidebar.right, a=1, b=?),
    LinearConstraint(POS_LTRB_OFFSET, y=header.left, x=root.left, a=1, b=?),
    # ... etc
]
```

### What Happens Next (Learning Phase)

The learning phase will:
1. Extract data from examples for each template
2. Use linear regression to infer parameters
3. For `header.height = b`: Learn `b ≈ 80` from both examples
4. For `sidebar.width = b`: Learn `b ≈ 200` from both examples
5. For `main.width = a · root.width`: Learn `a ≈ 0.75` (600/800) or `a ≈ 0.833` (1000/1200) - will need Bayesian approach to decide
6. For `sidebar.top = header.bottom + b`: Learn `b ≈ 0` from examples

But that's the **next phase** - instantiation just creates the sketches!

---

## Summary

Template instantiation is the first and most algorithmic phase of Mockdown:

✓ **Completely separate** from parameter learning
✓ **Input**: Multiple isomorphic layout examples (JSON hierarchies)
✓ **Output**: Constraint templates (form specified, parameters unknown)
✓ **Key steps**:
  1. Compute visibility graph (sweep-line algorithm)
  2. Build relationship matrices (vectorized)
  3. Identify valid patterns (boolean matrix operations)
  4. Generate constraint templates

✓ **Pruning strategies**:
  - Visibility graph: O(N²) → O(N) pairs
  - Semantic rules: Filter by relationships and types
  - Result: ~5-10 templates per view (manageable for learning)

✓ **Clean interface**: Templates have `sample_count=0` and default parameters, ready for learning

This is indeed a good starting point for reimplementation! The instantiation phase has clear inputs/outputs and doesn't depend on the learning or pruning phases.

