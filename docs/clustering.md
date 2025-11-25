# Parameter Clustering for Multi-Modal Constraint Learning

## The Problem

The current Mockdown design has a fundamental limitation when dealing with **structurally equivalent but parametrically different** examples.

### Example Scenario

```python
# Both examples have same structure (1-column layout)
example_1: authors.left = author1.left - 10  # narrow screen (width=400), small margin
example_2: authors.left = author1.left - 20  # also narrow (width=450), but larger margin

# Same template structure: authors.left = a * author1.left + b
# But different parameter values: b ∈ {-10, -20}
```

### Why This Fails

1. **Structural clustering groups them together** (both are 1-column layouts)
2. **Bayesian learning expects consistent parameters** across examples
3. **Linear regression fails** because the variance in `b` is too high
4. **Result**: Both constraints rejected OR averaged to `b = -15` (incorrect for both!)

### The Core Issue

- **Synthesis time**: MaxSMT picks ONE constraint set for all future uses
- **Runtime**: Kiwi solver applies that constraint set to new screen sizes
- **Missing**: MaxSMT doesn't know which parameter values apply to which screen sizes

## Proposed Solution: Clustering-Based Learning

Instead of fitting a single linear model to all examples, we:

1. **Cluster parameter values** to find multiple "modes"
2. **Learn decision functions** that map screen sizes to clusters
3. **Generate multiple constraint candidates**, each applicable to specific screen size ranges
4. **Let MaxSMT select** based on which candidates work for the test conformances

## Architecture

### Phase 1: Parameter Clustering

```python
def cluster_based_learning(templates, examples):
    """
    For each template, cluster parameter values and learn applicability.
    """
    candidates = []
    
    for template in templates:
        # Step 1: Extract (a, b, screen_size) from each example
        parameter_data = []
        for ex in examples:
            a, b = fit_template_to_example(template, ex)
            parameter_data.append({
                'a': a, 
                'b': b,
                'screen_width': ex.root.width,
                'screen_height': ex.root.height,
                'example_idx': ex.idx
            })
        
        # Step 2: Cluster parameter values
        # Use DBSCAN (auto-detects clusters) or KMeans (fixed k)
        from sklearn.cluster import DBSCAN
        X = np.array([[d['a'], d['b']] for d in parameter_data])
        clusters = DBSCAN(eps=0.5).fit(X)
        
        # Step 3: For each cluster, learn applicability
        for cluster_id in set(clusters.labels_):
            if cluster_id == -1:  # noise
                continue
            
            # Cluster center = constraint parameters
            cluster_mask = clusters.labels_ == cluster_id
            cluster_data = [d for d, mask in zip(parameter_data, cluster_mask) if mask]
            
            a_mean = np.mean([d['a'] for d in cluster_data])
            b_mean = np.mean([d['b'] for d in cluster_data])
            
            # Step 4: Learn decision function: screen_size → this cluster?
            X_screen = np.array([[d['screen_width'], d['screen_height']] 
                                  for d in parameter_data])
            y_cluster = (clusters.labels_ == cluster_id).astype(int)
            
            from sklearn.tree import DecisionTreeClassifier
            clf = DecisionTreeClassifier(max_depth=2)
            clf.fit(X_screen, y_cluster)
            
            # Create candidate with decision function
            candidate = LinearConstraint(
                y=template.y,
                x=template.x,
                a=a_mean,
                b=b_mean,
                score=compute_cluster_score(cluster_data),
                decision_fn=clf,  # NEW: captures applicability
                applicable_examples=[d['example_idx'] for d in cluster_data]
            )
            candidates.append(candidate)
    
    return candidates
```

### Phase 2: Cluster-Aware MaxSMT Pruning

```python
def maxsmt_with_clusters(candidates, test_conformances):
    """
    MaxSMT that evaluates decision functions on test screen sizes.
    """
    solver = Optimize()
    
    for c in candidates:
        # Evaluate: does this constraint apply to test screen sizes?
        applicability_scores = []
        for conf in test_conformances:
            screen = [conf.root.width, conf.root.height]
            # Probability that this constraint applies at this screen size
            prob = c.decision_fn.predict_proba([screen])[0][1]
            applicability_scores.append(prob)
        
        # Boost score based on applicability to test cases
        avg_applicability = np.mean(applicability_scores)
        boosted_score = c.score * avg_applicability
        
        # Add to MaxSMT with boosted score
        add_soft_constraint(solver, c, weight=boosted_score)
    
    # Rest of MaxSMT logic (axioms, uniqueness, etc.)
    # ...
```

## Alternative Approaches

### Option 1: Regression Trees (Simpler)

Learn `f(screen_size) → (a, b)` directly using decision trees:

```python
def regression_tree_learning(templates, examples):
    """
    Learn constraint parameters as functions of screen size.
    """
    for template in templates:
        X = [[ex.root.width, ex.root.height] for ex in examples]
        y_a = [fit_a(template, ex) for ex in examples]
        y_b = [fit_b(template, ex) for ex in examples]
        
        tree_a = DecisionTreeRegressor(max_depth=3).fit(X, y_a)
        tree_b = DecisionTreeRegressor(max_depth=3).fit(X, y_b)
        
        # Extract leaf nodes as discrete candidates
        for leaf in tree_a.leaves:
            a_pred = leaf.value
            b_pred = tree_b.predict(leaf.samples)
            screen_range = leaf.condition  # e.g., "width < 600"
            
            yield LinearConstraint(
                template.y, template.x, a_pred, b_pred,
                applicable_when=screen_range
            )
```

**Pros**: Directly learns parameter functions, interpretable
**Cons**: Requires more training data, may overfit

### Option 2: Simple Threshold Learning (Simplest)

For each template, detect if parameters are bimodal, then learn a threshold:

```python
def threshold_learning(templates, examples):
    """
    Detect parameter modes and learn simple thresholds.
    """
    for template in templates:
        b_values = [fit_b(template, ex) for ex in examples]
        
        # Detect if multimodal (e.g., using KDE or simple variance check)
        if variance(b_values) > THRESHOLD:
            # Cluster b values (e.g., k=2)
            clusters = kmeans(b_values, k=2)
            
            # Learn threshold that separates clusters
            # e.g., screen_width < 600 for cluster 0
            for cluster in clusters:
                threshold = learn_threshold(cluster.examples)
                yield LinearConstraint(
                    template.y, template.x,
                    a=mean(cluster.a_values),
                    b=mean(cluster.b_values),
                    applicable_when=f"width < {threshold}"
                )
```

**Pros**: Very simple, handles most common case (small vs large screens)
**Cons**: Only handles 1D thresholds, may miss complex patterns

### Option 3: Parameter-Based Sub-Clustering

Extend structural clustering to include parameter similarity:

```python
def conditional_template_instantiation_with_parameters(examples):
    # Step 1: Structural clustering (existing)
    structural_sets = cluster_by_structure(examples)
    
    # Step 2: Within each set, detect parameter variance
    for indices in structural_sets:
        set_examples = [examples[i] for i in indices]
        
        # Estimate parameter variance
        variance = estimate_parameter_variance(set_examples)
        
        if variance > THRESHOLD:
            # Split into sub-modes by parameter similarity
            sub_modes = cluster_by_parameter_similarity(set_examples)
            for sub_indices in sub_modes:
                yield sub_indices  # Treat as separate structural mode
        else:
            yield indices  # Keep as one mode
```

**Pros**: Minimal changes to existing architecture
**Cons**: Requires manual threshold tuning, treats parameter variation as structural difference

## Recommended Approach

**Short term (MVP)**: Option 2 (Simple Threshold Learning)
- Easiest to implement
- Handles the 80% case (small vs large screens)
- Can be added as post-processing to current Bayesian learning

**Long term (Research)**: Option 1 (Clustering + Decision Trees)
- More principled and general
- Handles arbitrary parameter distributions
- Better integration with MaxSMT

## Implementation Strategy

### Phase 1: Extend Data Types

```python
@dataclass
class LinearConstraint:
    y: Anchor
    x: Anchor
    a: float | None = None
    b: float | None = None
    score: float = 1.0
    decision_fn: Any = None  # NEW: sklearn classifier or lambda
    applicable_examples: list[int] = field(default_factory=list)  # NEW
```

### Phase 2: Modify Learning

```python
# In learning.py
def learn_constraints(templates, examples, method="clustering"):
    if method == "bayesian":
        return bayesian_learning(templates, examples)  # existing
    elif method == "clustering":
        return cluster_based_learning(templates, examples)  # new
    elif method == "threshold":
        return threshold_learning(templates, examples)  # new
```

### Phase 3: Modify MaxSMT Pruning

```python
# In pruning.py
def MaxSMTPruner.__call__(self, constraints, test_conformances):
    # Filter constraints by applicability to test cases
    for c in constraints:
        if c.decision_fn is not None:
            # Evaluate applicability
            applicability = evaluate_decision_fn(c, test_conformances)
            c.score *= applicability
    
    # Rest of MaxSMT logic
    # ...
```

## Open Questions

1. **How to evaluate decision functions at synthesis time?**
   - Need test conformances (screen sizes) to know which constraints apply
   - Current approach: use examples as test cases
   - Better: user provides target screen size ranges

2. **How to handle overlapping clusters?**
   - What if a constraint applies to multiple screen size ranges?
   - Solution: Allow multiple candidates, MaxSMT picks best

3. **How to choose clustering parameters?**
   - DBSCAN epsilon, KMeans k, decision tree depth
   - Could use cross-validation or heuristics

4. **Should this replace or augment Bayesian learning?**
   - Augment: Use Bayesian for single-mode, clustering for multi-mode
   - Replace: Always use clustering (more general)

## Related Work

- **CSS Media Queries**: Conditional styling based on screen size
- **Responsive Design Breakpoints**: Discrete screen size ranges
- **Mockdown's Structural Clustering**: Already handles discrete layout modes
- **Parametric Constraints**: Research area in constraint programming

## Next Steps

1. Implement simple threshold learning as proof of concept
2. Validate on examples with known parameter variance
3. Compare with current Bayesian approach
4. Extend to full clustering if threshold learning insufficient

