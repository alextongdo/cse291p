# Visibility Detection: Sweep-Line Algorithm

## Goal

Determine which pairs of view edges (anchors) have **uninterrupted line of sight** to each other. This filters which constraint templates are semantically valid during instantiation.

For example:
- A child's `left` edge is visible to its parent's `left` edge (they "see" each other)
- Two sibling views side-by-side have visible edges where they meet
- Views separated by another view do NOT have visibility

## What is an IntervalTree?

A data structure that stores **intervals** (line segments) and efficiently answers: *"Which intervals intersect this point?"*

Example:
```
Intervals: [0,10], [5,15], [20,30]
Query point 7: Returns [0,10] and [5,15]
Query point 25: Returns [20,30]
```

## The Algorithm

### 1. Build Interval Trees

For a parent view and its children:
- **Horizontal tree**: Stores all `top` and `bottom` edges (horizontal line segments)
  - Each edge stored as: `(left_x, right_x) → edge_object`
- **Vertical tree**: Stores all `left` and `right` edges (vertical line segments)
  - Each edge stored as: `(top_y, bottom_y) → edge_object`

### 2. Identify Event Points

**Events** are x/y coordinates where sweep lines should be cast:
- All `left` and `right` x-coordinates from every view (for vertical sweeps)
- All `top` and `bottom` y-coordinates from every view (for horizontal sweeps)

**Yes, we sweep at every view boundary coordinate!** This ensures we detect all adjacencies.

### 3. Sweep and Detect Adjacency

At each event point:

**Vertical sweep** (cast vertical line through horizontal edges):
```
For each x-coordinate:
  1. Query horizontal interval tree at x
  2. Sort intersecting edges by y-position
  3. Add parent's top/bottom edges to ends
  4. Adjacent pairs = visible pairs
```

**Horizontal sweep** (cast horizontal line through vertical edges):
```
For each y-coordinate:
  1. Query vertical interval tree at y
  2. Sort intersecting edges by x-position
  3. Add parent's left/right edges to ends
  4. Adjacent pairs = visible pairs
```

### 4. Examples

#### Example 1: Horizontal (Side-by-Side) Layout
```
        parent.top at y=0
┌─────────────────────┐ 
│  ┌────┐    ┌────┐  │ ← A.top, B.top at y=30
│  │ A  │    │ B  │  │
│  └────┘    └────┘  │ ← A.bottom, B.bottom at y=70
└─────────────────────┘
        parent.bottom at y=100

A: x=20 to x=60
B: x=100 to x=140  
Parent: x=0 to x=200
```

**All y-coordinates (horizontal sweep event points)**: 0, 30, 70, 100
- From parent: top=0, bottom=100
- From A: top=30, bottom=70
- From B: top=30, bottom=70

**Horizontal sweep at y=30** (where A.top and B.top are):
- Cast a **horizontal line** at y=30 across the entire layout
- This line intersects **vertical edges** (left/right edges of views)
- Which vertical edges does it hit? Any edge whose y-span includes 30

Intersecting **vertical edges** at y=30 (sorted left to right by x-position):
  - `parent.left` (at x=0, spans y=0 to y=100) ✓ includes y=30
  - `A.left` (at x=20, spans y=30 to y=70) ✓ includes y=30
  - `A.right` (at x=60, spans y=30 to y=70) ✓ includes y=30
  - `B.left` (at x=100, spans y=30 to y=70) ✓ includes y=30
  - `B.right` (at x=140, spans y=30 to y=70) ✓ includes y=30
  - `parent.right` (at x=200, spans y=0 to y=100) ✓ includes y=30

**Adjacent pairs** (consecutive in sorted list):
- `parent.left` ↔ `A.left` → visible ✓
- `A.right` ↔ `B.left` → **visible ✓ (gap between siblings!)**
- `B.right` ↔ `parent.right` → visible ✓

**Result**: `A.right` and `B.left` can see each other → spacing constraint

#### Example 2: Vertical (Stacked) Layout
```
    parent.left    parent.right
    x=0            x=100
    ↓              ↓
┌───────────┐
│  ┌─────┐  │ ← A.left at x=20, A.right at x=80
│  │  A  │  │
│  └─────┘  │
│           │  ← gap
│  ┌─────┐  │ ← B.left at x=20, B.right at x=80
│  │  B  │  │
│  └─────┘  │
└───────────┘

A: y=10 to y=40
B: y=60 to y=90
Parent: y=0 to y=100
```

**All x-coordinates (vertical sweep event points)**: 0, 20, 80, 100
- From parent: left=0, right=100
- From A: left=20, right=80
- From B: left=20, right=80

**Vertical sweep at x=20** (where A.left and B.left are):
- Cast a **vertical line** at x=20 down through the layout
- This line intersects **horizontal edges** (top/bottom edges of views)
- Which horizontal edges does it hit? Any edge whose x-span includes 20

Intersecting **horizontal edges** at x=20 (sorted top to bottom by y-position):
  - `parent.top` (at y=0, spans x=0 to x=100) ✓ includes x=20
  - `A.top` (at y=10, spans x=20 to x=80) ✓ includes x=20
  - `A.bottom` (at y=40, spans x=20 to x=80) ✓ includes x=20
  - `B.top` (at y=60, spans x=20 to x=80) ✓ includes x=20
  - `B.bottom` (at y=90, spans x=20 to x=80) ✓ includes x=20
  - `parent.bottom` (at y=100, spans x=0 to x=100) ✓ includes x=20

**Adjacent pairs**:
- `parent.top` ↔ `A.top` → visible ✓
- `A.bottom` ↔ `B.top` → **visible ✓ (gap between siblings!)**
- `B.bottom` ↔ `parent.bottom` → visible ✓

**Result**: `A.bottom` and `B.top` can see each other → spacing constraint

## Why This Matters

Visibility is used to filter constraint templates:
- **Offset constraints** (spacing): Only between visible position edges
- **Alignment constraints**: Only between visible, same-type edges

Without visibility filtering, we'd generate many spurious constraints like "left box's right edge relates to right box's left edge even though there's a box in between."

## Implementation Notes

- `interval_tree(root, primary_axis)`: Builds tree for one axis
- `visible_pairs(view, deep=True)`: Recursively computes pairs
- Returns `List[Tuple[IEdge, IEdge]]` of visible edge pairs
- Also adds `center_x` / `center_y` edges for alignment

