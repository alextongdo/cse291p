### Conditional Layouts

As mentioned in Section \ref{sec:improvements}, one improvement we want to make is to extend \textsc{Mockdown} to work on structurally different layouts. A part of our work so far has been developing a concrete algorithm to accomplish this goal. The following is a description of our approach.

The original \textsc{Mockdown} makes the assumption that all layout examples are structurally \textit{isomorphic}, allowing them to use the same set of layout constraints for all screen sizes. To support structurally different examples, we will need to write a recursive algorithm to parse each layout example and determine which ones belong to \textit{isomorphic sets}, or sets of layouts with the same structure. For each isomorphic set, we will instantiate a set of incomplete constraint sketches and union them all. Then, for each constraint sketch, we will perform Bayesian parameter inference with respect to only the examples in each isomorphic set. If we find any parameters that are the same (with threshold) for all isomorphic sets, we know that the layout constraint is global for all structurally different layouts. If the parameters are different, we know they should be conditionally applied and we should tag them with which isomorphic set they were derived from. Finally, when we solve the MaxSMT problem, we will conjunct all the conditional and global constraints together, except that we encode it such that each isomorphic set implies ($\Rightarrow$) its conditional constraints. This makes the conditional constraints vacuously true when the MaxSMT solver is not solving for a screen size where those constraints apply. The output of our algorithm is a set of conditional and global layout constraints that we can give to a Cassowary/Kiwi solver to get back a final layout.


### Problem: Isomorphic Structure ≠ Semantic Equivalence

We had assumed that for structurally different layouts, the examples would be \textit{isomorphically} different, but this turns out not to be true if we resize the root view. For example, a 3-column layout can be isomorphically the same as a 1-column layout (both have a parent with 3 children), but semantically they represent completely different layout behaviors. The children are positioned absolutely, meaning that as long as the parent view is large enough, similarly structured view hierarchies can produce structurally different layouts.

**Example:**
- **3-column layout** (wide screen): `authors` containing `[author1, author2, author3]` arranged horizontally
- **1-column layout** (narrow screen): `authors` containing `[author1, author2, author3]` arranged vertically stacked

These have identical tree structure but fundamentally different spatial relationships.


### Solution: Template-Based Layout Clustering

Instead of relying solely on tree isomorphism, we can leverage the **template instantiation** output to distinguish semantically different layouts. Since template instantiation uses the visibility algorithm (sweep-line) to determine which constraint templates are applicable, different layout modes will naturally produce **different sets of constraint templates**.

**Key Insight**: The visibility algorithm already encodes all structural information we need. We don't need to extract visibility signatures manually - we can simply compare the sets of instantiated templates!

#### Algorithm Overview

1. **Per-Example Template Instantiation**: For each example individually, run `template_instantiation([example])` to generate its constraint template set. This captures the spatial relationships (visibility) specific to that example's layout structure.

2. **Cluster by Template Set Equality**: Group examples that produce identical template sets into **layout mode clusters**. Examples with the same template set have the same structural behavior and should share constraint parameters.
   ```python
   # Pseudocode
   template_sets = {i: set(template_instantiation([examples[i]])) for i in range(len(examples))}
   clusters = group_by_set_equality(template_sets)
   ```

3. **Per-Cluster Constraint Learning**: For each layout mode cluster:
   - Use the cluster's template set (which is identical for all examples in the cluster)
   - Perform Bayesian learning using **only examples from this cluster**
   - This preserves mode association even for templates that appear in all modes

4. **Identify Global vs Conditional Constraints**: After learning per-cluster, analyze constraint categories:
   
   **a) Find structurally global templates:**
   ```python
   global_templates = set.intersection(*[template_sets[c] for c in clusters])
   ```
   
   **b) For each global template, check if parameters are identical:**
   - If all clusters learned the same parameters (within threshold) → **Truly Global Constraint**
   - If clusters learned different parameters → **Conditional Parameters** (tag each with its cluster)
   
   **c) Mode-specific templates** (not in intersection) are automatically **Conditional Structure**
   
   This produces three constraint categories:
   - **Truly Global**: Same structure AND same parameters (e.g., `root.width = authors.width + 0`)
   - **Conditional Structure**: Template only in some modes (e.g., `author1.right = author2.left - 30` only in horizontal)
   - **Conditional Parameters**: Template in all modes but different values (e.g., `authors.left = author1.left - 60` in wide, `- 10` in narrow)

5. **Unification Algorithm**: Merge constraints learned from different clusters:
   ```python
   # After per-cluster learning
   global_templates = set.intersection(*[template_sets[c] for c in clusters])
   
   truly_global = []
   conditional = []
   
   # Check global templates for parameter consistency
   for template in global_templates:
       learned_constraints = {}
       for cluster_id in clusters:
           # Find constraint matching this template in cluster's learned constraints
           for constraint in cluster_constraints[cluster_id]:
               if constraint.matches_template(template):
                   learned_constraints[cluster_id] = constraint
                   break
       
       # Compare parameters across clusters
       params = [(c.a, c.b) for c in learned_constraints.values()]
       if all_close(params, threshold=0.01):
           # Parameters match → truly global
           truly_global.append(learned_constraints[next(iter(clusters))])
       else:
           # Parameters differ → conditional
           for cluster_id, constraint in learned_constraints.items():
               conditional.append((cluster_id, constraint))
   
   # All mode-specific templates are conditional
   for cluster_id in clusters:
       mode_specific_templates = template_sets[cluster_id] - global_templates
       for constraint in cluster_constraints[cluster_id]:
           if constraint.template in mode_specific_templates:
               conditional.append((cluster_id, constraint))
   ```

6. **MaxSMT with Mode Selection**: Extend the MaxSMT formulation to include mode selection:
   - Add a categorical variable `layout_mode` that ranges over cluster IDs
   - For each conditional constraint `(cluster_id, constraint)`, add implication: `(layout_mode == cluster_id) ⇒ constraint`
   - Add truly global constraints unconditionally (no mode guard)
   - Add soft constraints that prefer each mode based on aspect ratio heuristics (e.g., wide screens prefer horizontal layout)
   - Solve to find optimal mode and constraint set

#### Template Set Comparison Example

For the 3-column vs 1-column example:

**3-column layout** (horizontal flow):
```python
templates_3col = {
    LinearConstraint(authors.left, author1.left, a=?, b=?),
    LinearConstraint(author1.right, author2.left, a=?, b=?),  # horizontal adjacency
    LinearConstraint(author2.right, author3.left, a=?, b=?),  # horizontal adjacency
    LinearConstraint(author1.top, author2.top, a=?, b=?),     # aligned tops
    # ... etc
}
```

**1-column layout** (vertical flow):
```python
templates_1col = {
    LinearConstraint(authors.left, author1.left, a=?, b=?),
    LinearConstraint(author1.bottom, author2.top, a=?, b=?),   # vertical adjacency
    LinearConstraint(author2.bottom, author3.top, a=?, b=?),   # vertical adjacency
    LinearConstraint(author1.left, author2.left, a=?, b=?),    # aligned lefts
    # ... etc
}
```

The set difference reveals mode-specific templates:
- `templates_3col - templates_1col` → horizontal adjacency constraints (author1.right to author2.left)
- `templates_1col - templates_3col` → vertical adjacency constraints (author1.bottom to author2.top)

These structural differences allow automatic clustering without manual signature extraction!

#### Why Learn Per-Cluster Matters: The Parameter Problem

Consider this scenario with a template that appears in **all** layout modes:

```python
# Template: authors.left = author1.left + b
# This structural relationship exists in both modes, but with different values:

# 3-column mode (wide screen, 1200px):
# authors.left = 0, author1.left = 60
# → authors.left = author1.left - 60

# 1-column mode (narrow screen, 500px):  
# authors.left = 0, author1.left = 10
# → authors.left = author1.left - 10
```

**If we learn using all examples together:**
- Bayesian learning sees: `b ∈ {-60, -10}`
- Produces mixture distribution with two peaks
- ❌ **Problem**: Both constraints are generated, but not tagged with which mode they came from
- MaxSMT solver can't know that `-60` goes with wide screens and `-10` with narrow screens

**If we learn per-cluster first:**
- Cluster 1 (3-column): `authors.left = author1.left - 60` tagged as `mode=horizontal`
- Cluster 2 (1-column): `authors.left = author1.left - 10` tagged as `mode=vertical`
- ✅ **Solution**: Each constraint is explicitly associated with its layout mode
- MaxSMT can apply mode guards: `(mode == horizontal) ⇒ b = -60`

This is why the unification algorithm checks parameter consistency - it distinguishes between:
- **Truly global**: `root.width = authors.width + 0` (same everywhere)
- **Conditional parameters**: `authors.left = author1.left + b` where `b` varies by mode

#### Complete Example: 3-Column vs 1-Column

**Input**: 2 examples at 1200×870 (horizontal), 2 examples at 500×1530 (vertical)

**Step 1: Template instantiation per-example**
```python
templates_example1 = {author1.right → author2.left, ...}  # horizontal adjacency
templates_example2 = {author1.right → author2.left, ...}  # same horizontal
templates_example3 = {author1.bottom → author2.top, ...}  # vertical adjacency
templates_example4 = {author1.bottom → author2.top, ...}  # same vertical

# Cluster by template set equality
cluster_horizontal = [example1, example2]
cluster_vertical = [example3, example4]
```

**Step 2: Learn per-cluster**
```python
# Horizontal cluster
constraints_h = bayesian_learning(templates_horizontal, [ex1, ex2])
# → author1.right = author2.left - 30 (score: 0.95)
# → authors.left = author1.left - 60 (score: 0.92)

# Vertical cluster  
constraints_v = bayesian_learning(templates_vertical, [ex3, ex4])
# → author1.bottom = author2.top + 0 (score: 0.98)
# → authors.left = author1.left - 10 (score: 0.90)
```

**Step 3: Unification**
```python
# Template "author1.right → author2.left" only in horizontal → Conditional Structure
# Template "authors.left = author1.left + b" in both, but b differs → Conditional Parameters
# Template "root.width = authors.width + 0" in both, same params → Truly Global

output = {
    "global": [
        LinearConstraint(root.width, authors.width, a=1, b=0)
    ],
    "conditional": [
        ("horizontal", LinearConstraint(author1.right, author2.left, a=1, b=-30)),
        ("horizontal", LinearConstraint(authors.left, author1.left, a=1, b=-60)),
        ("vertical", LinearConstraint(author1.bottom, author2.top, a=1, b=0)),
        ("vertical", LinearConstraint(authors.left, author1.left, a=1, b=-10)),
    ]
}
```

**Step 4: MaxSMT with mode selection (at inference time)**
```python
# For new screen size 800×600:
variables = [layout_mode ∈ {horizontal, vertical}, ...]
hard_constraints = [
    layout_axioms,  # width = right - left, etc.
    root.width = authors.width + 0,  # global
]
soft_constraints = [
    (layout_mode == horizontal) ⇒ (author1.right = author2.left - 30),
    (layout_mode == horizontal) ⇒ (authors.left = author1.left - 60),
    (layout_mode == vertical) ⇒ (author1.bottom = author2.top + 0),
    (layout_mode == vertical) ⇒ (authors.left = author1.left - 10),
    (width > height * 1.5) ⇒ prefer(layout_mode == horizontal),  # heuristic
]
# Solver picks: layout_mode = horizontal (since 800 > 600 * 1.5)
# Applies: horizontal constraints only
```

#### Mode Detection at Inference Time

When generating a layout for a new screen size, the MaxSMT solver will:
1. Receive as input the desired screen dimensions (width, height)
2. Add soft preferences for each mode (e.g., `prefer horizontal mode when width > height * 1.5`)
3. Select the optimal mode based on which constraints can be satisfied and maximize the total score
4. Apply only the constraints tagged with the selected mode (conditional constraints) plus all global constraints

This approach allows the system to automatically switch between layout modes (3-column ↔ 1-column) based on screen size, without requiring manual breakpoints or media queries.

#### Implementation Considerations

- **Template set comparison**: Use `frozenset` for hashable template sets to enable efficient clustering via dictionary/set operations
- **Hierarchical application**: Apply clustering recursively at each level of the view hierarchy, not just at the root level
- **Mode preferences**: Use simple heuristics (aspect ratio, screen size) as soft constraints, not hard rules
- **Constraint compatibility**: Ensure that conditional constraint sets are mutually exclusive to avoid conflicts during MaxSMT solving
- **Template equivalence**: Two templates are equivalent if they relate the same anchors (y, x), even if parameter values (a, b) differ. Implement `constraint.matches_template(y_anchor, x_anchor)` helper method.
- **Parameter comparison threshold**: When checking if parameters match across clusters, use `np.allclose(params1, params2, rtol=0.01)` to handle floating-point imprecision
- **Score preservation**: When creating truly global constraints, preserve the highest score from any cluster (or average scores across clusters)

By the end of the project, this visibility-based clustering approach should enable \textsc{Mockdown} to synthesize responsive layouts that adapt not just sizes, but entire layout structures, making it significantly more powerful for modern responsive web design.


### Implementation Plan: Phased Approach

To reduce risk and validate the core algorithm before implementing the full visibility-based detection, we will use a **phased implementation**:

#### Phase 1: Manual Layout Mode Tagging (Proof of Concept)

Instead of automatically detecting layout modes via visibility graphs, we will initially **manually tag examples** with their layout mode membership. This allows us to focus on implementing and validating the core conditional constraint algorithm.

**Input format example:**
```python
examples = [
    {
        "name": "root",
        "rect": [0, 0, 1200, 870],
        "layout_mode": "horizontal",  # Manual tag
        "children": [...]
    },
    {
        "name": "root",
        "rect": [0, 0, 500, 1530],
        "layout_mode": "vertical",  # Manual tag
        "children": [...]
    }
]
```

**Phase 1 Implementation Tasks:**
1. Extend input schema to accept `layout_mode` field (e.g., "horizontal", "vertical", "set1", "set2")
2. Group examples by manual `layout_mode` tags into mode groups
3. For each mode group, run template instantiation on **only that group's examples**:
   ```python
   mode_groups = group_by_manual_tag(examples)
   template_sets = {mode: template_instantiation(group) for mode, group in mode_groups.items()}
   ```
4. Learn constraints **separately for each mode group** using only that group's examples and templates
5. Implement unification algorithm to classify constraints as:
   - Truly global (same template and parameters across all modes)
   - Conditional structure (template only in some modes)
   - Conditional parameters (template in all modes, different parameters)
6. Extend MaxSMT formulation to include mode selection variable and conditional constraint implications:
   - Global constraints: always active
   - Conditional constraints: `(layout_mode == mode_id) ⇒ constraint`
7. Add soft preferences for modes based on screen aspect ratio
8. Validate that the system can correctly learn and apply mode-specific constraints

**Benefits of Phase 1:**
- Validates that per-mode learning and unification algorithm work correctly
- Confirms that conditional constraints and mode selection work correctly in MaxSMT
- Confirms MaxSMT formulation with mode guards is sound
- Allows testing with real examples without complex clustering logic
- Verifies that mode-tagged constraints correctly switch layout behavior at inference time
- Provides ground truth for validating Phase 2's automatic clustering

#### Phase 2: Automatic Template-Based Clustering

Once Phase 1 is validated and working, implement the automatic mode detection algorithm described above:

1. Modify template instantiation to run **per-example** (not on all examples together)
2. Implement template set comparison: group examples with identical template sets
3. Remove manual `layout_mode` tags and verify automatic clustering produces same groups
4. Validate that automatically detected modes produce equivalent constraints to manual tags

**Phase 2 Implementation:**
```python
# For each example, get its individual template set
template_sets = {}
for i, example in enumerate(examples):
    templates = template_instantiation([example])  # Single example
    # Use structural signature (y, x anchors) not full constraint (includes a, b)
    template_sigs = frozenset((t.y, t.x) for t in templates)
    template_sets[i] = (template_sigs, templates)

# Group examples by template signature equality
clusters = defaultdict(list)
for i, (sig, templates) in template_sets.items():
    clusters[sig].append((i, templates))

# Now learn constraints separately for each cluster
cluster_constraints = {}
for cluster_sig, cluster_data in clusters.items():
    example_indices = [i for i, _ in cluster_data]
    cluster_examples = [examples[i] for i in example_indices]
    # Use templates from first example (all have same structure)
    cluster_templates = cluster_data[0][1]
    cluster_constraints[cluster_sig] = bayesian_learning(cluster_templates, cluster_examples)

# Then run unification algorithm as described above...
```

**Important**: Template comparison must use **structural signature** (which anchors are related), not full constraint values (a, b parameters). Two templates are equivalent if `template1.y == template2.y` and `template1.x == template2.x`, regardless of their parameter values.

**Phase 2 Validation:**
- Run on Phase 1 test cases (with manual tags removed) and compare results
- Ensure template sets correctly distinguish horizontal vs vertical layouts
- Verify that 3-column examples cluster together and 1-column examples cluster together
- Confirm template-based clustering matches manual tagging

#### Phase 3: Extensions and Refinement

After core algorithm is working:
- Support hierarchical mode selection (different modes at different levels)
- Improve mode preference heuristics beyond simple aspect ratio
- Handle edge cases (mixed layouts, complex grid structures)
- Optimize signature matching for performance

This phased approach allows us to validate the conditional constraint synthesis algorithm independently of the clustering logic, reducing implementation risk and making debugging significantly easier.