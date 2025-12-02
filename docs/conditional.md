### Conditional Layouts

As mentioned in Section \ref{sec:improvements}, one improvement we want to make is to extend \textsc{Mockdown} to work on structurally different layouts. A part of our work so far has been developing a concrete algorithm to accomplish this goal. The following is a description of our approach.

The original \textsc{Mockdown} makes the assumption that all layout examples are structurally \textit{isomorphic}, allowing them to use the same set of layout constraints for all screen sizes. To support structurally different examples, we will need to write a recursive algorithm to parse each layout example and determine which ones belong to \textit{isomorphic sets}, or sets of layouts with the same structure. For each isomorphic set, we will instantiate a set of incomplete constraint sketches and union them all. Then, for each constraint sketch, we will perform Bayesian parameter inference with respect to only the examples in each isomorphic set. If we find any parameters that are the same (with threshold) for all isomorphic sets, we know that the layout constraint is global for all structurally different layouts. If the parameters are different, we know they should be conditionally applied and we should tag them with which isomorphic set they were derived from. Finally, when we solve the MaxSMT problem, we will conjunct all the conditional and global constraints together, except that we encode it such that each isomorphic set implies ($\Rightarrow$) its conditional constraints. This makes the conditional constraints vacuously true when the MaxSMT solver is not solving for a screen size where those constraints apply. The output of our algorithm is a set of conditional and global layout constraints that we can give to a Cassowary/Kiwi solver to get back a final layout.


### Problem: Isomorphic Structure ≠ Semantic Equivalence

We had assumed that for structurally different layouts, the examples would be \textit{isomorphically} different, but this turns out not to be true if we resize the root view. For example, a 3-column layout can be isomorphically the same as a 1-column layout (both have a parent with 3 children), but semantically they represent completely different layout behaviors. The children are positioned absolutely, meaning that as long as the parent view is large enough, similarly structured view hierarchies can produce structurally different layouts.

**Example:**
- **3-column layout** (wide screen): `authors` containing `[author1, author2, author3]` arranged horizontally
- **1-column layout** (narrow screen): `authors` containing `[author1, author2, author3]` arranged vertically stacked

These have identical tree structure but fundamentally different spatial relationships.





### MaxSMT Solving for Conditional Constraints: Complete Implementation Guide

#### Overview of MaxSMT in the Conditional Pipeline

MaxSMT pruning is the final stage after instantiation and learning. Its goal is to **remove conflicting constraints** while preserving the group-specific nature of conditional constraints. Unlike the unconditional case, we must now handle constraints that only apply to certain example groups.

**Key Principle**: Conditional constraints should only be tested against screen sizes from their associated examples. Testing constraints from group (0, 1) against screen sizes from group (2, 3) would be meaningless and could incorrectly prune valid constraints.

**Important Distinction**: 
- **Pruning time** (now): We test constraints against screen sizes from training examples
- **Inference time** (future): We apply learned constraints to new screen sizes not in training

At pruning time, we DON'T need implications or mode selection in MaxSMT - we simply route each constraint group to be tested only against its associated examples.

#### The Complete Conditional Constraint Pipeline

```
Input: Example layouts
  ↓
1. Template Instantiation (per-example)
   → Groups examples by template set similarity
   Output: {(0,1): [templates], (2,3): [templates]}
  ↓
2. Bayesian Learning (per-group)
   → Learns parameters for each group's constraints
   → Merges identical constraints across groups
   Output: {(0,1): [constraints], (0,1,2,3): [global_constraints], (2,3): [constraints]}
  ↓
3. MaxSMT Pruning (per-mode, this section)
   → Removes conflicts within each mode
   → Preserves mode tags in output
   Output: {(0,1): [pruned_constraints], (0,1,2,3): [pruned_global], (2,3): [pruned_constraints]}
  ↓
Final: Mode-conditional constraint set ready for deployment
```

#### Step-by-Step MaxSMT Implementation

**Input to MaxSMT Pruner**:
```python
# From conditional_bayesian_learning output:
conditional_constraints = {
    (0, 1): [constraint1, constraint2, ...],      # Constraints for examples 0, 1
    (2, 3): [constraint3, constraint4, ...],      # Constraints for examples 2, 3
    (0, 1, 2, 3): [global1, global2, ...],        # Global constraints (all examples)
}
examples = [example0, example1, example2, example3]  # Original examples
```

**The Algorithm (Very Simple!)**

```python
def conditional_hierarchical_pruning(
    conditional_constraints: dict[tuple[int, ...], list[LinearConstraint]],
    examples: list[View],
) -> dict[tuple[int, ...], list[LinearConstraint]]:
    """
    Hierarchical pruning for conditional constraints.
    
    CRITICAL: At inference time, we apply global constraints + group-specific constraints
    together. So they must be COMPATIBLE. We ensure this by pruning them together.
    
    Algorithm:
    1. Identify global constraints (apply to all examples)
    2. For each specific group:
       - Prune group_constraints + global_constraints TOGETHER using that group's examples
       - This ensures compatibility between group-specific and global constraints
    3. Global constraints = intersection of what survives across all groups
       (ensures global constraints work for EVERY group)
    """
    # Find global key (all example indices)
    all_indices = set()
    for key in conditional_constraints.keys():
        all_indices.update(key)
    global_key = tuple(sorted(all_indices))
    
    # Separate global from specific groups
    global_constraints = conditional_constraints.get(global_key, [])
    specific_groups = {k: v for k, v in conditional_constraints.items() if k != global_key}
    
    pruned_output = {}
    surviving_global_per_group = []
    
    # Prune each specific group together with global constraints
    for group_key, group_constraints in specific_groups.items():
        group_examples = [examples[i] for i in group_key]
        
        # Combine and prune together - ensures compatibility!
        combined = group_constraints + global_constraints
        pruned_combined = HierarchicalPruner(group_examples)(combined)
        
        # Separate back into group-specific vs global
        group_set = set(group_constraints)
        pruned_group = [c for c in pruned_combined if c in group_set]
        pruned_global = [c for c in pruned_combined if c not in group_set]
        
        pruned_output[group_key] = pruned_group
        surviving_global_per_group.append(set(pruned_global))
    
    # Global constraints must survive for ALL groups (intersection)
    if surviving_global_per_group:
        final_global = set.intersection(*surviving_global_per_group)
        pruned_output[global_key] = list(final_global)
    elif global_constraints:
        # No specific groups, just prune global constraints alone
        all_examples = examples
        pruned_output[global_key] = HierarchicalPruner(all_examples)(global_constraints)
    
    return pruned_output
```

**Why We Must Prune Together**:

Consider this scenario:
```python
# After learning:
Global (0,1,2,3): root.width = authors.width + 0       (score: 0.95)
Group (0,1):      root.width = topbar.width + 0        (score: 0.90)
Group (2,3):      root.width = search.width + 0        (score: 0.88)
```

At inference time for a screen size similar to examples 0,1, you'll apply:
```python
constraints_to_apply = constraints[(0,1,2,3)] + constraints[(0,1)]
                    = [root.width = authors.width] + [root.width = topbar.width]
```

**These constraints conflict!** They require `authors.width == topbar.width`, which may not be true.

If we pruned them separately:
- Global constraints tested against all examples → both might survive
- Group (0,1) constraints tested against examples 0,1 → might survive
- **Problem**: Never tested together, so conflict not detected!

By pruning them together using examples 0,1, MaxSMT will detect the conflict and choose one:
- Either keep global `root.width = authors.width` (higher score, drop group-specific)
- Or keep group `root.width = topbar.width` (more specific to this group)

**Global Constraint Intersection**:

Global constraints must survive pruning against **every** group's examples:
```python
# Prune global + group(0,1) using examples 0,1 → global_constraints_a survive
# Prune global + group(2,3) using examples 2,3 → global_constraints_b survive
# Final global = global_constraints_a ∩ global_constraints_b
```

This ensures global constraints truly work for all layout modes!

**No MaxSMT Modifications Needed!**

Your existing `HierarchicalPruner` and `MaxSMTPruner` classes don't need ANY changes. They already handle conditional constraints correctly when you pass the right examples.

**Output Format**

The output preserves the group structure:
```python
{
    (0, 1, 2, 3): [pruned_global_constraints],  # Apply to all examples
    (0, 1): [pruned_constraints_for_group_01],   # Apply only to examples 0, 1
    (2, 3): [pruned_constraints_for_group_23],   # Apply only to examples 2, 3
}
```

---

## Inference Time: Applying Constraints to New Screen Sizes (Future Work)

**Important**: The above pruning algorithm is complete for the current implementation. What follows is for FUTURE deployment when you need to apply learned constraints to screen sizes not in your training data.

---

When generating a layout for a new screen size (not in training examples), you need to determine which constraint group to use:

**Option A: Heuristic-Based Group Selection (Simpler, Recommended)**
```python
def infer_group_from_screen_size(width, height, training_examples, constraint_groups):
    """
    Use simple heuristics to determine which constraint group a new screen size belongs to.
    Match to the group with the most similar average screen size/aspect ratio.
    """
    aspect_ratio = width / height
    
    # Compute average characteristics for each group
    group_characteristics = {}
    for group_key in constraint_groups.keys():
        group_examples = [training_examples[i] for i in group_key]
        avg_aspect = np.mean([ex.width / ex.height for ex in group_examples])
        avg_width = np.mean([ex.width for ex in group_examples])
        avg_height = np.mean([ex.height for ex in group_examples])
        group_characteristics[group_key] = (avg_aspect, avg_width, avg_height)
    
    # Find closest group (can use aspect ratio, absolute size, or both)
    closest_group = min(
        group_characteristics.keys(), 
        key=lambda k: abs(group_characteristics[k][0] - aspect_ratio)
    )
    return closest_group

# Usage at inference time:
new_width, new_height = 800, 600
active_group = infer_group_from_screen_size(new_width, new_height, examples, pruned_constraints)

# Apply global constraints + group-specific constraints
global_key = tuple(range(len(examples)))  # e.g., (0, 1, 2, 3)
constraints_to_apply = (
    pruned_constraints.get(global_key, []) + 
    pruned_constraints[active_group]
)

# Now use Kiwi/Cassowary solver with these constraints to generate layout
```

**Option B: Solver-Based Group Selection (More Flexible, Advanced)**

**This is when you'd need implications in MaxSMT!** You'd extend the solver to include group selection as a variable:

```python
# This is FUTURE work - adds implications to Z3 for inference-time mode selection
def solve_with_mode_selection(screen_width, screen_height, conditional_constraints):
    """
    Let the solver automatically choose which constraint group to apply.
    Uses implications: (group_var == i) ⇒ constraints[i]
    """
    solver = z3.Optimize()
    
    # Add group selection variable
    num_groups = len([k for k in conditional_constraints.keys() if len(k) < len(examples)])
    group_var = z3.Int('constraint_group')
    solver.add(z3.Or([group_var == i for i in range(num_groups)]))
    
    # For each group's constraints, add as implications
    for group_id, (group_key, constraints) in enumerate(conditional_constraints.items()):
        if group_key == global_key:
            # Global constraints always apply (no implication)
            for constraint in constraints:
                z3_constraint = constraint_to_z3_expr(constraint, ...)
                solver.add_soft(z3_constraint, weight=constraint.score)
        else:
            # Group-specific constraints use implications
            for constraint in constraints:
                z3_constraint = constraint_to_z3_expr(constraint, ...)
                # (group_var == group_id) ⇒ z3_constraint
                solver.add_soft(
                    z3.Implies(group_var == group_id, z3_constraint),
                    weight=constraint.score
                )
    
    # Add soft preferences for groups based on heuristics
    aspect_ratio = screen_width / screen_height
    for group_id, group_key in enumerate(constraint_groups):
        group_examples = [examples[i] for i in group_key]
        group_aspect = np.mean([ex.width / ex.height for ex in group_examples])
        
        # Prefer groups with similar aspect ratio
        similarity = 1.0 / (1.0 + abs(aspect_ratio - group_aspect))
        solver.add_soft(group_var == group_id, weight=int(similarity * 100))
    
    # Solve and extract chosen group
    if solver.check() == z3.sat:
        model = solver.model()
        chosen_group = model.eval(group_var).as_long()
        return chosen_group
```

**Note**: Option B requires significant extension to your MaxSMT solver and is only needed if you want the solver to automatically switch between groups at inference time. For most use cases, Option A (heuristic-based) is simpler and sufficient.

#### Implementation Checklist

**For Current Pruning Implementation (Do Now):**

- [x] **Created `conditional_hierarchical_pruning` function** in `src/pruning.py` ✓
- [ ] **Call `conditional_hierarchical_pruning`** instead of standard `hierarchical_pruning` when you have conditional constraints
- [x] **No changes to `MaxSMTPruner` or `HierarchicalPruner`** - they already work correctly ✓
- [x] **Preserve group tags** through the pruning process (input dict keys → output dict keys) ✓

**For Future Inference Implementation (Later):**

- [ ] **Implement group selection heuristic** (Option A) or solver-based selection (Option B)
- [ ] **(Option B only)** Add implication support to MaxSMT for group-conditional constraints
- [ ] **Integrate with deployment pipeline** to apply correct constraints for new screen sizes

#### Key Insights

1. **Must prune group + global constraints together**: At inference, we apply both. If we prune separately, conflicts might slip through. Pruning them together ensures compatibility.

2. **Global constraints = intersection across groups**: A "global" constraint must survive pruning with EVERY group's examples. We take the intersection to ensure this.

3. **No synthetic test sizes needed**: You don't manually create test screen sizes. The `min_rect` and `max_rect` computed from each group's examples automatically provide appropriate test cases.

4. **Conditional pruning is still simple**: Despite the added logic, it's still a clean wrapper around the existing pruner. The core MaxSMT logic needs ZERO changes.

4. **Group tags flow through the entire pipeline**: 
   - Instantiation: `{(0,1): templates, (2,3): templates}` ← Groups by template similarity
   - Learning: `{(0,1): constraints, (2,3): constraints, (0,1,2,3): global}` ← Learns per-group, merges identical
   - Pruning: `{(0,1): pruned, (2,3): pruned, (0,1,2,3): pruned_global}` ← Prunes per-group
   - Inference (future): "New screen 800×600 → matches group (0,1) → apply constraints[(0,1)] + constraints[(0,1,2,3)]"

5. **Implications only needed for inference**: Z3 implications `(condition) → (constraint)` are ONLY needed if you want the solver to automatically choose between groups at deployment time (Option B). For simple heuristic-based group selection (Option A), no MaxSMT changes are needed.

6. **Hierarchical groups**: In principle, each level of the view hierarchy could have different groups (e.g., root has 2 groups, child container has 3 groups). The algorithm naturally supports this by running conditional instantiation/learning/pruning recursively at each level.

This design keeps the MaxSMT solver simple while enabling powerful conditional layout synthesis!