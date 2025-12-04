# Conditional Constraint Pruning: Option A vs Option B

## The Problem

With clustering-based parameter learning, we get **overlapping constraint groups**:

```python
{
    (0,): 49 constraints,      # Only applies to example 0
    (0, 1): 3 constraints,     # Applies to examples 0 AND 1
    (0, 1, 2): 8 constraints,  # Global (all examples)
    (1,): 19 constraints,
    (1, 2): 23 constraints,
    (2,): 22 constraints,
}
```

When applying constraints to example 0, we need constraints from `(0,)`, `(0, 1)`, and `(0, 1, 2)` to all be **jointly satisfiable**.

---

## Option A: Per-Example Pruning (Current Implementation)

### Algorithm

```python
def prune(conditional_constraints, examples):
    # Step 1: Map each example to all constraints that apply to it
    example_to_constraints = defaultdict(list)
    for group, constraints in conditional_constraints.items():
        for example_idx in group:
            example_to_constraints[example_idx].extend(constraints)
    
    # Step 2: Prune per-example
    survived_per_example = {}
    for example_idx, constraints in example_to_constraints.items():
        pruned = HierarchicalPruner([examples[example_idx]]).prune(constraints)
        survived_per_example[example_idx] = set(pruned)
    
    # Step 3: Constraint survives if it survives for ALL examples in its group
    output = defaultdict(list)
    for group, constraints in conditional_constraints.items():
        for c in constraints:
            if all(c in survived_per_example[e] for e in group):
                output[group].append(c)
    return output
```

### Complexity: Simple

- Reuses existing `HierarchicalPruner` unchanged
- O(num_examples) independent MaxSMT solves
- Each solve is small (constraints for one example)
- ~30 lines of new code

---

## Option B: Single MaxSMT with Conditional Encoding

### Algorithm

```python
def prune(conditional_constraints, examples):
    # Step 1: Generate test rects per example
    example_to_test_rects = {}
    for i, ex in enumerate(examples):
        rect = TestRect(left=ex.left, top=ex.top, width=ex.width, height=ex.height)
        example_to_test_rects[i] = [rect]  # Could expand to range
    
    # Step 2: Build constraint -> applicable examples mapping
    constraint_to_group = {}
    all_constraints = []
    for group, constraints in conditional_constraints.items():
        for c in constraints:
            constraint_to_group[c] = group
            all_constraints.append(c)
    
    # Step 3: Single MaxSMT solve with conditional encoding
    h_solver = z3.Optimize()
    v_solver = z3.Optimize()
    
    constraint_vars = {}
    for idx, c in enumerate(all_constraints):
        z3_var = z3.Bool(f"c_{idx}")
        constraint_vars[c] = z3_var
        
        solver = h_solver if c.y.is_horizontal() else v_solver
        solver.add_soft(z3_var, weight=int(c.score * 1000))
    
    # Step 4: Add conditional implications
    # Constraint only needs to hold for test rects from applicable examples
    for c in all_constraints:
        applicable_examples = constraint_to_group[c]
        z3_var = constraint_vars[c]
        solver = h_solver if c.y.is_horizontal() else v_solver
        
        for example_idx in applicable_examples:
            for rect_idx, test_rect in enumerate(example_to_test_rects[example_idx]):
                global_rect_id = f"{example_idx}_{rect_idx}"
                
                # Add layout axioms for this test rect (if not already added)
                add_layout_axioms_if_needed(solver, global_rect_id, test_rect)
                
                # If constraint selected, it must hold for this test rect
                expr = constraint_to_z3_expr(c, global_rect_id)
                solver.add(z3.Implies(z3_var, expr))
    
    # Step 5: Solve and extract survivors
    # ... (similar to existing MaxSMTPruner)
    
    # Step 6: Reconstruct output by group
    output = defaultdict(list)
    for c in all_constraints:
        if constraint_survived(c):
            output[constraint_to_group[c]].append(c)
    return output
```

### Complexity: Significantly More Complex

**New code required:**
- Custom MaxSMT setup (can't reuse `HierarchicalPruner` directly)
- Track which test rects belong to which examples
- Avoid duplicate layout axiom additions
- Handle hierarchical decomposition with conditional test rects
- ~150+ lines of new code

**Additional challenges:**
1. **Hierarchical decomposition**: Original pruner infers child bounds from parent solution. With multiple examples having different structures, this becomes complex.
2. **Test rect management**: Need unique IDs for test rects across examples
3. **Layout axiom deduplication**: Same test rect shouldn't get axioms added twice

---

## Comparison Summary

| Aspect | Option A | Option B |
|--------|----------|----------|
| Code complexity | ~30 lines | ~150+ lines |
| Reuses existing code | Yes (HierarchicalPruner) | No (custom MaxSMT setup) |
| Number of Z3 solves | O(num_examples) | O(1) |
| Solve size | Small (per-example) | Large (all constraints) |
| Global optimality | No (independent solves) | Yes (single solve) |
| Handles overlaps | Yes (intersection) | Yes (native) |

**Recommendation**: Start with Option A. Only move to Option B if you observe suboptimal pruning due to independent solves.

---

## Adding Proper Test Rect Ranges

### The Problem

Currently, Option A uses a single example per solve, which means `min_rect == max_rect` (no range). This doesn't test intermediate screen sizes.

### Solution for Option A: Per-Group Range Computation

Instead of testing each constraint at exactly one screen size, **compute the range from all examples in the constraint's group**.

```python
def prune(conditional_constraints, examples):
    # Step 1: Compute test rect range for each group
    group_to_rect_range = {}
    for group in conditional_constraints.keys():
        group_examples = [examples[i] for i in group]
        min_rect = TestRect(
            left=min(ex.left for ex in group_examples),
            top=min(ex.top for ex in group_examples),
            width=min(ex.width for ex in group_examples),
            height=min(ex.height for ex in group_examples),
        )
        max_rect = TestRect(
            left=max(ex.left for ex in group_examples),
            top=max(ex.top for ex in group_examples),
            width=max(ex.width for ex in group_examples),
            height=max(ex.height for ex in group_examples),
        )
        group_to_rect_range[group] = (min_rect, max_rect)
    
    # Step 2: For each example, determine the WIDEST range needed
    # (union of ranges from all groups containing this example)
    example_to_rect_range = {}
    for example_idx in range(len(examples)):
        applicable_groups = [g for g in conditional_constraints.keys() if example_idx in g]
        
        all_mins = [group_to_rect_range[g][0] for g in applicable_groups]
        all_maxs = [group_to_rect_range[g][1] for g in applicable_groups]
        
        combined_min = TestRect(
            left=min(r.left for r in all_mins),
            top=min(r.top for r in all_mins),
            width=min(r.width for r in all_mins),
            height=min(r.height for r in all_mins),
        )
        combined_max = TestRect(
            left=max(r.left for r in all_maxs),
            top=max(r.top for r in all_maxs),
            width=max(r.width for r in all_maxs),
            height=max(r.height for r in all_maxs),
        )
        example_to_rect_range[example_idx] = (combined_min, combined_max)
    
    # Step 3: Prune per-example using computed range
    survived_per_example = {}
    for example_idx, constraints in example_to_constraints.items():
        min_rect, max_rect = example_to_rect_range[example_idx]
        
        # Create a "fake" example list that gives us the right rect range
        # HierarchicalPruner computes range from examples, so we need to
        # create synthetic examples at min/max bounds
        synthetic_examples = create_synthetic_examples(
            examples[example_idx], min_rect, max_rect
        )
        
        pruned = HierarchicalPruner(synthetic_examples).prune(constraints)
        survived_per_example[example_idx] = set(pruned)
    
    # Step 4: Same intersection logic as before
    # ...
```

**Key insight**: For each example, compute the widest test rect range needed (union of all applicable groups' ranges). This ensures constraints are tested across all relevant screen sizes.

### Solution for Option B: Native Range Per Group

Option B handles this more naturally:

```python
def prune(conditional_constraints, examples):
    # Generate test rects spanning each group's range
    for group, constraints in conditional_constraints.items():
        group_examples = [examples[i] for i in group]
        min_rect = compute_min_rect(group_examples)
        max_rect = compute_max_rect(group_examples)
        test_rects = test_rect_range(min_rect, max_rect, num=5)
        
        for c in constraints:
            for rect_idx, test_rect in enumerate(test_rects):
                # Constraint must hold for ALL test rects in its group's range
                solver.add(z3.Implies(constraint_var[c], constraint_to_z3(c, rect_idx)))
```

**Key difference**: In Option B, each constraint is only tested on its own group's range. In Option A, we test all applicable constraints together using the widest needed range.

---

## Implementation Complexity for Range Support

| Aspect | Option A with Ranges | Option B with Ranges |
|--------|---------------------|---------------------|
| Additional code | ~40 lines | ~20 lines |
| Conceptual complexity | Medium (synthetic examples) | Low (native) |
| Test rect management | Need to pass range to HierarchicalPruner | Built into single solve |

**Conclusion**: Adding range support is cleaner in Option B, but Option A's approach (using synthetic examples to set the range) is a reasonable workaround that maintains code reuse.

