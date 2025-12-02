# Clustering-Based Multi-Mode Parameter Learning

## The Problem

The current Bayesian learning assumes all examples follow the same linear relationship. When examples have multiple parameter modes, it fails:

```python
# Template: parent.left = child.left + b

Example 0: parent.left=0, child.left=10  → b = -10
Example 1: parent.left=0, child.left=10  → b = -10
Example 2: parent.left=0, child.left=50  → b = -50
Example 3: parent.left=0, child.left=50  → b = -50

# Current Bayesian learning:
# Data: y=[0,0,0,0], x=[10,10,50,50]
# GLM fit: y = a*x + b tries to fit all points
# Result: High residual variance → REJECTED
```

But we SHOULD learn:
```python
Constraint 1: parent.left = child.left - 10  (applies to examples 0, 1)
Constraint 2: parent.left = child.left - 50  (applies to examples 2, 3)
```

## The Solution: Cluster Then Learn

### Algorithm Overview

Instead of fitting one model to all examples, we:
1. **Detect parameter clusters** in the data
2. **Learn separately** for each cluster using existing Bayesian learning
3. **Tag constraints** with which examples they apply to

This naturally leverages the existing A space, B space, and Stern-Brocot priors!

### Detailed Algorithm

```python
def cluster_based_learning(
    template: LinearConstraint,
    examples: list[View],
    config: LearningConfig
) -> list[LinearConstraint]:
    """
    Learn multiple constraints for a template when examples exhibit parameter modes.
    
    Returns:
        List of constraints, each tagged with applicable example indices
    """
    # Step 1: Extract actual anchor values from examples
    y_values = [get_anchor_value(ex, template.y) for ex in examples]
    
    if template.x is not None:
        x_values = [get_anchor_value(ex, template.x) for ex in examples]
    else:
        x_values = None
    
    # Step 2: Compute "implied parameters" for each example
    # These are the (a, b) that would perfectly fit each individual example
    implied_params = []
    
    if template.x is None:
        # Constant form: y = b
        implied_params = [(0, y) for y in y_values]
    elif template.b == 0.0:
        # Multiplicative form: y = a*x
        implied_params = [(y/x if x != 0 else 0, 0) for y, x in zip(y_values, x_values)]
    elif template.a == 1.0:
        # Additive form: y = x + b
        implied_params = [(1, y - x) for y, x in zip(y_values, x_values)]
    else:
        # General form: y = a*x + b
        # We can't uniquely determine (a, b) from one example, so use b only
        # (Assume a will be learned from cluster trend)
        implied_params = [(None, y - x) for y, x in zip(y_values, x_values)]
    
    # Step 3: Cluster examples by implied parameters
    clusters = cluster_parameters(implied_params, distance_threshold=...)
    
    # Step 4: For each cluster, run standard Bayesian learning
    results = []
    for cluster_indices in clusters:
        cluster_examples = [examples[i] for i in cluster_indices]
        
        # Use existing Bayesian learning!
        learned = bayesian_learning(
            templates=[template],
            examples=cluster_examples,
            config=config
        )
        
        # Tag with applicable examples
        for constraint in learned:
            constraint.applicable_examples = cluster_indices
        
        results.extend(learned)
    
    return results
```

### Parameter Clustering Algorithm

The key is choosing a clustering method that respects the A/B space structure:

```python
def cluster_parameters(
    implied_params: list[tuple[float, float]],
    b_threshold: int = 5,
    a_threshold: float = 0.1
) -> list[list[int]]:
    """
    Cluster examples by their implied parameters using hierarchical clustering.
    
    Uses distance metric that respects:
    - Absolute distance for 'b' (offset)
    - Relative distance for 'a' (scale)
    
    Args:
        implied_params: List of (a, b) tuples for each example
        b_threshold: Max difference in b to be same cluster (e.g., 10 vs 15 → cluster)
        a_threshold: Max relative difference in a (e.g., 1.0 vs 1.05 → cluster)
    
    Returns:
        List of clusters, where each cluster is a list of example indices
    """
    from scipy.cluster.hierarchy import linkage, fcluster
    from scipy.spatial.distance import pdist
    
    n = len(implied_params)
    
    # Handle trivial cases
    if n <= 1:
        return [[i] for i in range(n)]
    
    # Custom distance function
    def param_distance(i, j):
        a_i, b_i = implied_params[i]
        a_j, b_j = implied_params[j]
        
        # Distance in b space (absolute)
        b_dist = abs(b_i - b_j) / b_threshold
        
        # Distance in a space (relative, if both defined)
        if a_i is not None and a_j is not None:
            a_avg = (abs(a_i) + abs(a_j)) / 2 + 1e-10
            a_dist = abs(a_i - a_j) / (a_avg * a_threshold)
        else:
            a_dist = 0  # Ignore a if not computable
        
        # Combined distance (max gives conservative clustering)
        return max(b_dist, a_dist)
    
    # Build distance matrix
    distances = pdist(range(n), metric=param_distance)
    
    # Hierarchical clustering with threshold=1.0
    # (distance > 1.0 means parameters differ by more than threshold)
    linkage_matrix = linkage(distances, method='complete')
    cluster_labels = fcluster(linkage_matrix, t=1.0, criterion='distance')
    
    # Group by cluster label
    clusters = {}
    for idx, label in enumerate(cluster_labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(idx)
    
    return list(clusters.values())
```

### Why This Works

**Leverages A/B Space**: Each cluster is learned using standard Bayesian learning, which:
- Searches over A space (Farey sequence)
- Searches over B space (integer ball)
- Applies Stern-Brocot priors (favors simple fractions)

**Example**: 
```python
# Cluster 1: margin = 10 ± noise
# Bayesian learning sees [10, 10, 11, 10]
# Finds candidates: b ∈ [8, 12] → {8, 9, 10, 11, 12}
# Scores using prior + likelihood
# Result: b=10 (highest posterior, simplest)

# Cluster 2: margin = 50 ± noise  
# Bayesian learning sees [50, 49, 50, 51]
# Finds candidates: b ∈ [47, 53] → {47, 48, ..., 53}
# Result: b=50 (highest posterior)
```

The priors automatically handle "33/100 vs 1/3" - even if data says 0.33, the prior strongly favors 1/3!

### Confidence Intervals Still Apply

Within each cluster, Bayesian learning computes confidence intervals normally:

```python
# Cluster with [10, 10, 11, 10]
# GLM fit: b ≈ 10.25, confidence interval [9.5, 11.0]
# Candidates: {9, 10, 11}
# Posteriors: {9: 0.1, 10: 0.8, 11: 0.1}  ← prior favors round numbers!
# Output: LinearConstraint(..., b=10, score=0.8)
```

This means even with small noise, the algorithm finds the "simplest" value in the confidence region.

### Integration with Conditional Learning

This slots perfectly into your existing `conditional_bayesian_learning`:

```python
def conditional_bayesian_learning(
    example_idxs_to_templates_map: dict[tuple, list[LinearConstraint]],
    examples: list[View],
    seed: int | None = None,
    config: LearningConfig | None = None,
    enable_clustering: bool = True,  # New parameter
) -> dict[tuple[int, ...], list[LinearConstraint]]:
    
    constr_to_sets_map = defaultdict(set)
    constr_to_max_score_map = {}
    
    for example_idxs, templates in example_idxs_to_templates_map.items():
        set_examples = [examples[i] for i in example_idxs]
        
        if enable_clustering:
            # Use clustering-based learning
            learned_constraints = cluster_based_bayesian_learning(
                templates=templates,
                examples=set_examples,
                seed=seed,
                config=config
            )
        else:
            # Use standard learning
            learned_constraints = bayesian_learning(
                templates=templates,
                examples=set_examples,
                seed=seed,
                config=config
            )
        
        # Rest of merging logic remains the same...
```

### When Clustering Helps

**Scenario 1: Multi-mode within structural set**
```python
# All same structure (same visibility), but different margins
Examples [0,1]: margin = 10  (wide screens)
Examples [2,3]: margin = 50  (narrow screens)

Without clustering: REJECTED (high variance)
With clustering: Two constraints, each applicable to subset
```

**Scenario 2: Noise tolerance for globals**
```python
# Structural set A: margin = 10
# Structural set B: margin = 11

Without clustering: Separate constraints (10 ≠ 11)
With clustering: If clusters merge, becomes global constraint
```

### Clustering Threshold Selection

**Conservative (small threshold)**: 
- `b_threshold = 2-3`: Only cluster very similar values (10 vs 11)
- Avoids false merging
- Good for clean data

**Aggressive (large threshold)**:
- `b_threshold = 10-20`: Cluster broad ranges (10 vs 20)
- Tolerates more noise
- Risk of false positives

**Adaptive (recommended)**:
```python
# Scale threshold by data magnitude
b_threshold = max(5, 0.1 * median(|b_values|))

# For margins ~100: threshold = 10 (10% tolerance)
# For margins ~10: threshold = 5 (50% tolerance, but absolute min)
```

### Alternative: Density-Based Clustering (DBSCAN)

Instead of hierarchical clustering, use DBSCAN:

```python
from sklearn.cluster import DBSCAN

def cluster_parameters_dbscan(implied_params, eps=5, min_samples=2):
    """
    Use DBSCAN to find parameter clusters.
    
    Advantages:
    - Automatically determines number of clusters
    - Handles outliers (noise points)
    - No need to specify distance threshold
    
    Args:
        eps: Max distance for points to be in same neighborhood
        min_samples: Min points to form a cluster
    """
    # Extract b values (most important for clustering)
    b_values = np.array([b for a, b in implied_params]).reshape(-1, 1)
    
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(b_values)
    labels = clustering.labels_
    
    # Group by cluster (-1 = noise)
    clusters = {}
    for idx, label in enumerate(labels):
        if label == -1:
            # Outlier: put in its own cluster
            clusters[f'noise_{idx}'] = [idx]
        else:
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
    
    return list(clusters.values())
```

### Complete Example

```python
# Input:
Template: parent.left = child.left + b
Examples:
  0: parent.left=0, child.left=10
  1: parent.left=0, child.left=10
  2: parent.left=0, child.left=50
  3: parent.left=0, child.left=51

# Step 1: Implied parameters
implied_params = [(None, -10), (None, -10), (None, -50), (None, -51)]

# Step 2: Cluster (b_threshold=5)
# Distance: |-10 - (-10)| = 0 → same cluster
# Distance: |-50 - (-51)| = 1 → same cluster  
# Distance: |-10 - (-50)| = 40 → different clusters
Clusters: [[0, 1], [2, 3]]

# Step 3: Learn per cluster
# Cluster [0,1]: Bayesian learning on examples 0,1
#   y=[0,0], x=[10,10]
#   CI for b: [-11, -9]
#   Candidates: {-11, -10, -9}
#   Result: b=-10 (highest posterior)

# Cluster [2,3]: Bayesian learning on examples 2,3
#   y=[0,0], x=[50,51]
#   CI for b: [-52, -49]
#   Candidates: {-52, -51, -50, -49}
#   Result: b=-50 (round number, higher prior)

# Output:
[
  LinearConstraint(parent.left, child.left, a=1, b=-10, 
                   score=0.9, applicable_examples=[0,1]),
  LinearConstraint(parent.left, child.left, a=1, b=-50,
                   score=0.85, applicable_examples=[2,3])
]
```

## Summary

**Key advantages of this approach:**

1. ✅ **Leverages existing infrastructure**: Uses A/B space, priors, confidence intervals
2. ✅ **Respects simplicity bias**: 1/3 still preferred over 33/100 within clusters
3. ✅ **Automatic mode detection**: Finds parameter clusters without manual specification
4. ✅ **Clean integration**: Slots into existing `conditional_bayesian_learning` pipeline
5. ✅ **Interpretable**: Each constraint explicitly tagged with applicable examples

**Implementation complexity**: Medium
- Need to add clustering step before Bayesian learning
- Need to track applicable examples through pipeline
- Rest of system remains unchanged

**Research contribution**: High
- Novel synthesis approach (not just detection)
- Handles multi-mode parameters the original Mockdown cannot
- Maintains mathematical rigor (Bayesian inference + priors)

