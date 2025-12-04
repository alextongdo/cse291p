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
    
    # Step 2: Compute observed parameter value for each example
    # Mockdown only learns ONE parameter at a time, so we just need the relevant one
    
    if template.x is None:
        # Constant form: y = b → observed b = y
        observed_values = y_values
        clusters = cluster_1d(observed_values, b_threshold=config.b_cluster_threshold)
    elif template.b == 0.0:
        # Multiplicative form: y = a*x → observed a = y/x
        observed_values = [y/x if x != 0 else 0 for y, x in zip(y_values, x_values)]
        clusters = cluster_1d(observed_values, a_threshold=config.a_cluster_threshold)
    else:  # template.a == 1.0
        # Additive form: y = x + b → observed b = y - x
        observed_values = [y - x for y, x in zip(y_values, x_values)]
        clusters = cluster_1d(observed_values, b_threshold=config.b_cluster_threshold)
    
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

**Key simplification**: Mockdown only learns ONE parameter at a time:
- **Constant form** (`y = b`): Cluster by `b` values (absolute threshold)
- **Multiplicative form** (`y = a*x`): Cluster by `a` values (relative threshold)
- **Additive form** (`y = x + b`): Cluster by `b` values (absolute threshold)

So we don't need complex multi-dimensional clustering - just cluster on the single learnable parameter!

**Important**: `b` values use **absolute** threshold (e.g., |10-15| ≤ 5), while `a` values use **relative** threshold (e.g., |1.0-1.1|/1.05 ≤ 0.1).

```python
def cluster_1d(
    values: list[float],
    a_threshold: float | None = None,
    b_threshold: float | None = None,
) -> list[list[int]]:
    """
    Cluster 1D values using greedy gap-based clustering.

    Sorts values, then greedily groups consecutive values whose gap
    is within the threshold. Exactly one threshold must be provided.

    Args:
        values: List of values to cluster
        a_threshold: Relative threshold for ratio values (e.g., 0.1 = 10% difference)
        b_threshold: Absolute threshold for offset values (e.g., 5 = |v1-v2| ≤ 5)

    Returns:
        List of clusters, where each cluster is a list of indices into `values`

    Example:
        >>> cluster_1d([10, 50, 12, 48], b_threshold=5)
        [[0, 2], [1, 3]]  # [10, 12] and [48, 50] are grouped
    """
    if (a_threshold is None) == (b_threshold is None):
        raise ValueError("Exactly one of a_threshold or b_threshold must be provided")

    n = len(values)
    if n <= 1:
        return [[i] for i in range(n)]

    sorted_indices = sorted(range(n), key=lambda i: values[i])
    clusters = [[sorted_indices[0]]]

    for i in range(1, n):
        curr_idx = sorted_indices[i]
        prev_idx = sorted_indices[i - 1]
        curr_val = values[curr_idx]
        prev_val = values[prev_idx]

        if a_threshold is not None:
            # Relative distance for ratios
            avg_val = (abs(curr_val) + abs(prev_val)) / 2 + 1e-10
            gap = abs(curr_val - prev_val) / avg_val
            threshold = a_threshold
        else:
            # Absolute distance for offsets
            gap = abs(curr_val - prev_val)
            threshold = b_threshold

        if gap <= threshold:
            clusters[-1].append(curr_idx)
        else:
            clusters.append([curr_idx])

    return clusters
```

**Why absolute for `b`, relative for `a`:**
```python
# For b (offsets): absolute makes sense
# b=10 vs b=15: diff=5 → reasonable to cluster if threshold=5
# b=100 vs b=105: diff=5 → also reasonable (5px is 5px)

# For a (ratios): relative makes sense  
# a=1.0 vs a=1.1: 10% diff → cluster together
# a=0.1 vs a=0.2: 100% diff → should NOT cluster!
# (If we used absolute: |0.1-0.2|=0.1 would wrongly cluster them)
```

**Why this is simpler:**
- No scipy dependency needed
- O(n log n) instead of O(n²) 
- Easy to understand and debug

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

`ConditionalBayesianLearning` uses clustering by default - it's the key innovation:

```python
class ConditionalBayesianLearning:
    """Bayesian learning with clustering-based parameter mode detection."""
    
    def learn(
        self,
        example_idxs_to_templates_map: dict[tuple, list[LinearConstraint]],
    ) -> dict[tuple[int, ...], list[LinearConstraint]]:
        
        for example_idxs, templates in example_idxs_to_templates_map.items():
            for template in templates:
                # Cluster examples by observed parameter values
                clusters = self._cluster_template_examples(template, example_idxs)
                
                # Learn separately for each cluster
                for cluster_example_idxs in clusters:
                    cluster_examples = [self.examples[i] for i in cluster_example_idxs]
                    learned = BayesianLearning(
                        examples=cluster_examples, config=self.config
                    ).learn([template])
                    # ... merge logic ...
```

If you want standard Mockdown learning without clustering, use `BayesianLearning` directly.

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

**For `b` (offsets) - absolute threshold:**
- `b_threshold = 3-5`: Conservative, only cluster very similar values (10 vs 12)
- `b_threshold = 10-15`: Tolerates more noise (10 vs 20)

**For `a` (ratios) - relative threshold:**
- `a_threshold = 0.05`: Conservative, 5% difference (1.0 vs 1.05)
- `a_threshold = 0.1`: Tolerates 10% difference (1.0 vs 1.1)

**Examples:**
```python
# b_threshold = 5 (absolute)
# |10 - 15| = 5 ≤ 5 → same cluster ✓
# |10 - 20| = 10 > 5 → different clusters ✓

# a_threshold = 0.1 (relative, 10%)
# |1.0 - 1.1| / 1.05 = 0.095 ≤ 0.1 → same cluster ✓
# |1.0 - 1.5| / 1.25 = 0.40 > 0.1 → different clusters ✓
# |0.1 - 0.2| / 0.15 = 0.67 > 0.1 → different clusters ✓ (100% diff!)
```

**Adaptive (recommended):**
```python
# For b: scale by data magnitude with minimum
b_threshold = max(5, 0.1 * median(|b_values|))

# For a: fixed relative threshold
a_threshold = 0.1  # 10% tolerance
```

### Complete Example

```python
# Input:
Template: parent.left = child.left + b  (additive form, a=1 fixed)
Examples:
  0: parent.left=0, child.left=10  → implied b = 0 - 10 = -10
  1: parent.left=0, child.left=10  → implied b = 0 - 10 = -10
  2: parent.left=0, child.left=50  → implied b = 0 - 50 = -50
  3: parent.left=0, child.left=51  → implied b = 0 - 51 = -51

# Step 1: Observed b values (computed from examples)
observed_values = [-10, -10, -50, -51]

# Step 2: Cluster (b_threshold=5)
# Sorted: [-51, -50, -10, -10] with indices [3, 2, 0, 1]
# 
# Start cluster: [3] (value -51)
# -50 vs -51: |diff| = 1 ≤ 5 → add to cluster: [3, 2]
# -10 vs -50: |diff| = 40 > 5 → new cluster: [0]
# -10 vs -10: |diff| = 0 ≤ 5 → add to cluster: [0, 1]
#
# Result: [[3, 2], [0, 1]]  (or equivalently [[2,3], [0,1]])

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
6. ✅ **Simple implementation**: Just 1D clustering on the learnable parameter (a OR b, never both)

**Implementation complexity**: Low-Medium
- Add ~20 line clustering function
- Call it before Bayesian learning for each template
- Track applicable examples through pipeline
- No external dependencies (scipy/sklearn not needed)

**Research contribution**: High
- Novel synthesis approach (not just detection)
- Handles multi-mode parameters the original Mockdown cannot
- Maintains mathematical rigor (Bayesian inference + priors)

