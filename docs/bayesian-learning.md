# Parameter Learning - Bayesian Inference

## Overview

Parameter learning is the second phase of the Mockdown pipeline. It takes constraint templates (with unknown parameters) from the instantiation phase and infers concrete parameter values by fitting them to the example layouts using Bayesian inference.

**Key characteristics:**
- Takes templates with form specified but unknown parameters (`y = a·x + b` where `a` or `b` are unknown)
- Uses multiple layout examples to infer parameter values through statistical regression
- Outputs multiple candidate constraints with confidence scores for each template
- Supports both simple learning (perfect fit) and noise-tolerant Bayesian learning

**Relationship to instantiation:**
- **Completely separate phase** - runs after instantiation is complete
- Templates from instantiation have `sample_count=0` and default parameter values
- Learning fills in the unknown parameters and sets `sample_count=N` where N = number of examples

---

## Input Format

### Constraint Templates

Templates are the output from the instantiation phase. Each template specifies the constraint form but has unknown parameters.

**Example Input Templates**:
```python
[
    # Constant constraint: header.height = b (unknown)
    ConstantConstraint(
        kind=ConstraintKind.SIZE_CONSTANT,
        y_id=AnchorID("header", Attribute.HEIGHT),
        x_id=None,
        a=Rational(0),      # Fixed (no x term)
        b=Rational(0),      # UNKNOWN - default value
        op=operator.eq,
        sample_count=0      # Template marker
    ),
    
    # Ratio constraint: sidebar.width = a · root.width (unknown a)
    LinearConstraint(
        kind=ConstraintKind.SIZE_RATIO,
        y_id=AnchorID("sidebar", Attribute.WIDTH),
        x_id=AnchorID("root", Attribute.WIDTH),
        a=Rational(1),      # UNKNOWN - default value
        b=Rational(0),      # Fixed (no constant term)
        op=operator.eq,
        sample_count=0
    ),
    
    # Offset constraint: main.top = 1 · header.bottom + b (unknown b)
    LinearConstraint(
        kind=ConstraintKind.POS_LTRB_OFFSET,
        y_id=AnchorID("main", Attribute.TOP),
        x_id=AnchorID("header", Attribute.BOTTOM),
        a=Rational(1),      # Fixed (multiplier is 1)
        b=Rational(0),      # UNKNOWN - default value
        op=operator.eq,
        sample_count=0
    ),
]
```

### Layout Examples

The same examples used for instantiation, now used to extract numerical data:

**Example Data** (2 examples):
```python
# Example 1: 800×600
{
    "header": {"height": 80, "bottom": 80},
    "sidebar": {"width": 200},
    "root": {"width": 800},
    "main": {"top": 80}
}

# Example 2: 1200×800
{
    "header": {"height": 80, "bottom": 80},
    "sidebar": {"width": 200},
    "root": {"width": 1200},
    "main": {"top": 80}
}
```

---

## Output Format

### Constraint Candidates with Scores

Each template can produce **multiple candidate constraints** with different parameter values and confidence scores.

**Example Output**:
```python
[
    # For template: header.height = b
    [
        ConstraintCandidate(
            constraint=ConstantConstraint(
                y_id=AnchorID("header", HEIGHT),
                b=Rational(80),           # Learned: height is 80px
                sample_count=2            # Based on 2 examples
            ),
            score=0.95                     # High confidence
        )
    ],
    
    # For template: sidebar.width = a · root.width
    [
        ConstraintCandidate(
            constraint=LinearConstraint(
                y_id=AnchorID("sidebar", WIDTH),
                x_id=AnchorID("root", WIDTH),
                a=Rational(1, 4),          # Learned: width is 1/4 of root
                b=Rational(0),
                sample_count=2
            ),
            score=0.60                     # Medium confidence
        ),
        ConstraintCandidate(
            constraint=LinearConstraint(
                y_id=AnchorID("sidebar", WIDTH),
                x_id=AnchorID("root", WIDTH),
                a=Rational(1, 5),          # Alternative: 1/5 of root
                b=Rational(0),
                sample_count=2
            ),
            score=0.25                     # Lower confidence
        )
    ],
    
    # For template: main.top = header.bottom + b
    [
        ConstraintCandidate(
            constraint=LinearConstraint(
                y_id=AnchorID("main", TOP),
                x_id=AnchorID("header", BOTTOM),
                a=Rational(1),
                b=Rational(0),             # Learned: b=0 (aligned)
                sample_count=2
            ),
            score=0.98                     # Very high confidence
        )
    ],
]
```

**Key fields**:
- `constraint`: The template with learned parameters filled in
- `score`: Confidence/probability score (0-1)
- `sample_count`: Set to N (number of examples)
- Multiple candidates per template represent uncertainty

---

## Algorithm Steps

### Step 0: Extract Template Data

For each template, extract the relevant anchor values from all examples.

```python
def extract_data(template: IConstraint, examples: List[IView]) -> pd.DataFrame:
    """
    Extract y and x values for a template from all examples.
    
    Returns DataFrame with columns [y_id, x_id] (or just [y_id] for constants)
    """
    if template.kind.is_constant_form:
        # Only need y values
        data = [[example.find_anchor(template.y_id).value] 
                for example in examples]
        return pd.DataFrame(data, columns=[str(template.y_id)])
    else:
        # Need both y and x values
        data = [[example.find_anchor(template.y_id).value,
                 example.find_anchor(template.x_id).value]
                for example in examples]
        return pd.DataFrame(data, columns=[str(template.y_id), str(template.x_id)])
```

**Example extraction** for `sidebar.width = a · root.width`:
```python
# Template data from 2 examples:
    root.width  sidebar.width
0         800            200
1        1200            200

# Will learn: a = sidebar.width / root.width
# Example 1: a = 200/800 = 0.25 = 1/4
# Example 2: a = 200/1200 = 0.167 = 1/6
# Inconsistent! Need Bayesian approach to handle this.
```

---

### Learning Methods

Mockdown provides three learning methods, from simplest to most sophisticated:

---

### Method 1: Simple Learning (Perfect Fit)

**When to use**: Examples are perfect (no noise), parameters should be identical across examples.

**Algorithm**:
```python
class SimpleLearning:
    def learn_template(self, template: IConstraint) -> ConstraintCandidate:
        """Learn parameters assuming perfect data."""
        constants = {}
        
        for i, example in enumerate(self.examples):
            # Extract anchor values
            y_value = example.find_anchor(template.y_id).value
            x_value = example.find_anchor(template.x_id).value if template.x_id else None
            
            # Compute parameters based on constraint form
            if template.kind == ConstraintKind.SIZE_CONSTANT:
                # y = b
                a = 0
                b = y_value
                
            elif template.kind in {ConstraintKind.SIZE_RATIO, 
                                  ConstraintKind.SIZE_ASPECT_RATIO}:
                # y = a·x (ratio form, b=0)
                a = y_value / x_value
                b = 0
                
            elif template.kind == ConstraintKind.POS_LTRB_OFFSET:
                # y = x + b (offset form, a=1)
                a = 1
                b = y_value - x_value
            
            # Check consistency with previous examples
            if i > 0:
                if not math.isclose(old_a, a, rel_tol=0.01):
                    raise ConstraintFalsified(template)
                if not math.isclose(old_b, b, rel_tol=0.01):
                    raise ConstraintFalsified(template)
            
            constants = {'a': a, 'b': b}
        
        # Rationalize the learned constants
        a_rational = Rational(constants['a']).limit_denominator(100)
        b_rational = Rational(constants['b']).limit_denominator(100)
        
        # Return single candidate with learned parameters
        learned_constraint = template.subst(a=a_rational, b=b_rational, 
                                           sample_count=len(self.examples))
        return [ConstraintCandidate(learned_constraint, score=1.0)]
```

**Example**:
```python
# Template: header.height = b
# Example 1: header.height = 80
# Example 2: header.height = 80
# Learned: b = 80, score = 1.0 ✓

# Template: sidebar.width = a · root.width
# Example 1: 200 = a · 800  => a = 0.25
# Example 2: 200 = a · 1200 => a = 0.167
# Inconsistent! Template FALSIFIED ✗
```

**Pros**:
- Fast and simple
- Works well for clean data
- Easy to understand

**Cons**:
- **Fails on inconsistent data** - rejects templates if parameters differ between examples
- No handling of measurement noise
- No uncertainty quantification

---

### Method 2: Heuristic Learning (Simple + Scoring)

Extension of Simple Learning with heuristic scoring to rank candidates.

**Algorithm**: Same as Simple Learning, but adds heuristic scores based on:
- **Simplicity bias**: Prefer small numerators/denominators
- **Zero bias**: Prefer b=0 (alignment) over non-zero offsets
- **Constant bias**: Prefer size constants with round numbers

```python
def build_biases(self, constraints: List[IConstraint]) -> Dict[IConstraint, float]:
    scores = {}
    for c in constraints:
        score = 1.0
        
        # Prefer small, "nice" fractions
        if c.a.p < 25: score *= 10      # Numerator < 25
        if c.a.p < 10: score *= 10      # Numerator < 10
        if c.a.p > 100: return 1        # Penalize large numerators
        
        # Prefer zero offsets (alignment)
        if c.kind.is_position_kind:
            if abs(c.b) == 0:
                score = 1000            # Strong preference for alignment
            elif abs(c.b) < 25:
                score = 1000 - 40*abs(c.b)  # Linear decay
            else:
                score = 10              # Penalize large offsets
        
        scores[c] = score
    return scores
```

**Pros**:
- Still fast
- Incorporates domain knowledge through heuristics
- Provides relative scores for pruning

**Cons**:
- Still fails on inconsistent data
- Heuristics are hand-tuned, not principled
- No probabilistic interpretation

---

### Method 3: Noise-Tolerant Bayesian Learning (Recommended)

**When to use**: Real-world data with noise, need uncertainty quantification, want principled statistical approach.

**Core Idea**: Use Bayesian inference to find parameter values that best fit the data, accounting for measurement noise.

---

#### Step 1: Candidate Space Construction

Define discrete candidate spaces for parameters:

**a-space** (for ratios): Extended Farey sequence
```python
def ext_farey(max_denom=100) -> np.ndarray:
    """
    Generate all rational numbers with denominator ≤ max_denom,
    extended beyond [0,1] to include reciprocals.
    
    Examples: [0, 1/100, 1/99, ..., 1/2, ..., 1, 2, 3, ..., 100]
    """
    # Standard Farey sequence F_100: all fractions 0 ≤ p/q ≤ 1, q ≤ 100
    farey = sorted({Fraction(p, q) 
                    for q in range(1, max_denom+1) 
                    for p in range(0, q+1)})
    
    # Extend with reciprocals > 1
    extended = farey + [1/f for f in reversed(farey[1:-1])]
    return np.array(extended)
```

**b-space** (for offsets): Integer ball
```python
def z_ball(center=0, radius=1000) -> np.ndarray:
    """
    All integers in [-radius, radius].
    
    Examples: [-1000, -999, ..., 0, 1, ..., 1000]
    """
    return np.arange(-radius, radius+1, dtype=int)
```

**Typical sizes**:
- a-space: ~5,000 candidates (all fractions with denominator ≤ 100)
- b-space: ~2,000 candidates (integers from -1000 to 1000)

---

#### Step 2: Generalized Linear Model (GLM) Fitting

For each template, fit a GLM to the data with constraints on the form.

**Model**: `y = a·x + b + ε` where `ε ~ N(0, σ²)`

```python
def fit_template_model(template: IConstraint, data: pd.DataFrame) -> GLMFit:
    """
    Fit GLM with form constraints based on template kind.
    """
    x = sm.add_constant(data[x_col])  # Add intercept column
    y = data[y_col]
    
    # Add tiny noise to avoid perfect separation errors
    x += np.random.randn(len(x)) * 1e-5
    y += np.random.randn(len(y)) * 1e-5
    
    model = sm.GLM(y, x)
    
    # Constrain based on form
    if template.kind.is_constant_form:
        # y = b (force a=0)
        # Constraint: (0*b) + (1*a) = 0 => a must be 0
        fit = model.fit_constrained(((0, 1), 0))
        
    elif template.kind.is_mul_only_form:
        # y = a·x (force b=0)
        # Constraint: (1*b) + (0*a) = 0 => b must be 0
        fit = model.fit_constrained(((1, 0), 0))
        
    elif template.kind.is_add_only_form:
        # y = x + b (force a=1)
        # Constraint: (0*b) + (1*a) = 1 => a must be 1
        fit = model.fit_constrained(((0, 1), 1))
        
    else:
        # Full form: y = a·x + b (no constraints)
        fit = model.fit()
    
    return fit
```

**Special case for single example**:
When there's only 1 example, add a synthetic data point to make regression possible:
- For constants: Duplicate the point
- For ratios: Add point `(x, y) = (0, 0)` (enforces line through origin)
- For offsets: Add point that preserves the computed offset

---

#### Step 3: Confidence Intervals

Compute confidence intervals for parameters using the fitted GLM:

```python
def get_confidence_intervals(fit: GLMFit, config: Config) -> Tuple[Interval, Interval]:
    """
    Get confidence intervals for a and b from GLM fit.
    
    Uses specified alpha levels (default: 95% confidence = alpha=0.025 two-tailed)
    """
    # GLM fit.conf_int returns DataFrame with columns [lower, upper]
    # Rows are [b, a] (intercept first, then coefficient)
    
    a_lower, a_upper = fit.conf_int(alpha=config.a_alpha).iloc[1]  # Row 1 = coefficient
    b_lower, b_upper = fit.conf_int(alpha=config.b_alpha).iloc[0]  # Row 0 = intercept
    
    return (a_lower, a_upper), (b_lower, b_upper)
```

**Example**:
```python
# Template: sidebar.width = a · root.width
# Data: [(800, 200), (1200, 200)]
# GLM fit with b=0 constraint
#   => a_fit = 0.20 (best fit line)
#   => 95% CI: a ∈ [0.15, 0.25]
```

---

#### Step 4: Candidate Filtering

Find candidates in the confidence intervals:

```python
def filter_candidates(a_space, b_space, a_confint, b_confint):
    """
    Find all candidates whose values fall within the confidence intervals.
    """
    a_lower, a_upper = a_confint
    b_lower, b_upper = b_confint
    
    # Find candidates in a-space within [a_lower, a_upper]
    a_candidates = a_space[(a_space >= a_lower) & (a_space <= a_upper)]
    
    # Handle edge case: CI is between two candidates
    if len(a_candidates) == 0:
        # Find nearest candidates on either side
        a_center = (a_lower + a_upper) / 2
        idx = np.searchsorted(a_space, a_center)
        a_candidates = [a_space[max(0, idx-1)], a_space[min(idx, len(a_space)-1)]]
    
    # Same for b-space
    b_candidates = b_space[(b_space >= b_lower) & (b_space <= b_upper)]
    if len(b_candidates) == 0:
        b_center = (b_lower + b_upper) / 2
        idx = np.searchsorted(b_space, b_center)
        b_candidates = [b_space[max(0, idx-1)], b_space[min(idx, len(b_space)-1)]]
    
    # Cartesian product of candidates
    candidates = [(a, b) for a in a_candidates for b in b_candidates]
    return candidates
```

**Example continuation**:
```python
# CI: a ∈ [0.15, 0.25]
# Farey candidates in this range: [1/6, 1/5, 1/4]
# => 3 candidates for a

# CI: b ∈ [-0.5, 0.5]  
# Integer candidates in this range: [0]
# => 1 candidate for b

# Total: 3 × 1 = 3 candidate pairs:
#   (1/6, 0), (1/5, 0), (1/4, 0)
```

---

#### Step 5: Likelihood Scoring

Score each candidate using the GLM log-likelihood:

```python
def likelihood_score(model: GLM, a: Fraction, b: Fraction) -> float:
    """
    Compute log-likelihood of data given parameters (a, b).
    """
    return model.loglike((b, a))  # Note: GLM expects (intercept, coeff)
```

Convert to probabilities and normalize:
```python
candidates['glm_loglike'] = [likelihood_score(model, a, b) for (a,b) in candidates]
candidates['glm_score'] = np.exp(candidates['glm_loglike'])
candidates['glm_score'] /= candidates['glm_score'].sum()  # Normalize to sum=1
```

---

#### Step 6: Prior Scoring

Apply a prior that prefers simpler fractions using Stern-Brocot depth:

**Stern-Brocot Depth**: Measure of fraction complexity
```python
def sb_depth(fraction: Fraction) -> int:
    """
    Depth in Stern-Brocot tree = sum of continued fraction terms.
    
    Examples:
    - 1/2 = [0; 2]           => depth = 2   (simple)
    - 1/3 = [0; 3]           => depth = 3
    - 2/5 = [0; 2, 2]        => depth = 4
    - 7/13 = [0; 1, 1, 6]    => depth = 8   (complex)
    """
    cf = continued_fraction(fraction)
    return sum(cf)
```

**Prior distribution**: Beta-binomial favoring small depths
```python
def compute_prior(a_space, expected_depth=5, max_depth=100):
    """
    Compute prior probabilities favoring simpler fractions.
    
    Uses beta-binomial distribution over depths.
    """
    depths = np.array([sb_depth(a) for a in a_space])
    
    # Beta-binomial parameters
    alpha = expected_depth + 1
    beta = (max_depth - expected_depth) + 1
    
    # Probability mass for each depth level
    depth_probs = [stats.betabinom.pmf(k, max_depth, alpha, beta) 
                   for k in range(max_depth+1)]
    
    # Assign to candidates and normalize within each depth
    priors = []
    for d in depths:
        # Probability for this depth level
        prob = depth_probs[d]
        # Divided by number of fractions at this depth (uniform within depth)
        prob /= np.sum(depths == d)
        priors.append(prob)
    
    return np.array(priors)
```

**Intuition**: 
- Simple fractions like 1/2, 1/3, 2/3 are more likely in UI constraints
- Complex fractions like 47/83 are unlikely
- Prior "pulls" towards simplicity, but data can override

---

#### Step 7: Posterior Scoring

Combine likelihood and prior via Bayes' rule:

```python
# Posterior ∝ Likelihood × Prior
candidates['posterior'] = candidates['glm_score'] * candidates['prior_score']
candidates['posterior'] /= candidates['posterior'].sum()  # Normalize
```

Sort by posterior score and return top candidates:

```python
def learn_template(template: IConstraint) -> List[ConstraintCandidate]:
    """Complete Bayesian learning for one template."""
    # Steps 1-7 above
    candidates = compute_posterior_candidates(template)
    
    # Convert to ConstraintCandidate objects
    results = []
    for _, row in candidates.iterrows():
        learned_constraint = template.subst(
            a=Rational(row['a']), 
            b=Rational(row['b']),
            sample_count=len(examples)
        )
        results.append(ConstraintCandidate(learned_constraint, row['posterior']))
    
    return sorted(results, key=lambda c: -c.score)  # Descending score
```

---

#### Step 8: Rejection Criteria

Reject templates that don't fit the data well:

```python
def reject_template(template: IConstraint, data: pd.DataFrame, fit: GLMFit) -> bool:
    """
    Reject if template doesn't explain the data well.
    """
    x, y = data[x_col], data[y_col]
    
    # Reject if no variance in x but large variance in y
    if np.var(x) == 0 and np.std(y) > cutoff_spread:
        return True  # Can't explain y variance without x variance
    
    # Reject if no variance in y but large variance in x
    if np.var(y) == 0 and np.std(x) > cutoff_spread:
        return True  # y doesn't depend on x
    
    # Reject if residuals are too large (poor fit)
    if np.std(fit.resid_response) > cutoff_spread:
        return True  # Model doesn't fit data
    
    return False  # Accept
```

**Example rejections**:
```python
# Template: sidebar.width = a · root.width
# Data: sidebar.width = [200, 200], root.width = [800, 1200]
# => var(sidebar.width) = 0, var(root.width) > 0
# => REJECT (sidebar width doesn't vary with root width)

# Template: sidebar.width = b (constant)
# Data: sidebar.width = [200, 200]
# => var(sidebar.width) = 0, residuals ≈ 0
# => ACCEPT (good fit)
```

---

## Complete Example

### Input

**Templates** (from instantiation):
```python
[
    LinearConstraint(sidebar.width = a · root.width, a=?, b=0),
    ConstantConstraint(sidebar.width = b),
]
```

**Examples**:
```
Example 1: root.width=800,  sidebar.width=200
Example 2: root.width=1200, sidebar.width=200
```

### Execution

**Template 1**: `sidebar.width = a · root.width`

```python
# Step 1: Extract data
data = pd.DataFrame({
    'root.width': [800, 1200],
    'sidebar.width': [200, 200]
})

# Step 2: Fit GLM with b=0 constraint
# Best fit: a ≈ 0.20
# CI: a ∈ [0.15, 0.25]

# Step 3: Find candidates
# Farey candidates: [1/6=0.167, 1/5=0.20, 1/4=0.25]

# Step 4: Score candidates
Candidate       GLM Likelihood  Prior   Posterior
a=1/6, b=0      0.15           0.30     0.045
a=1/5, b=0      0.70           0.35     0.245     <- Best fit
a=1/4, b=0      0.15           0.35     0.052

# But also check rejection criteria
# var(sidebar.width) = 0, var(root.width) > 0
# => REJECT! (sidebar doesn't vary with root)
```

**Template 2**: `sidebar.width = b`

```python
# Step 1: Extract data
data = pd.DataFrame({
    'sidebar.width': [200, 200]
})

# Step 2: Fit GLM with a=0 constraint
# Best fit: b = 200
# CI: b ∈ [199.5, 200.5]

# Step 3: Find candidates
# Integer candidates: [200]

# Step 4: Score
Candidate    GLM Likelihood  Posterior
b=200        1.0             1.0

# Rejection check
# var(sidebar.width) = 0, residuals ≈ 0
# => ACCEPT (perfect constant fit)
```

### Output

```python
[
    [  # Candidates for template 1
        # (empty - rejected)
    ],
    [  # Candidates for template 2
        ConstraintCandidate(
            ConstantConstraint(sidebar.width = 200, sample_count=2),
            score=1.0
        )
    ]
]
```

---

## Configuration Parameters

### NoiseTolerantLearningConfig

```python
@dataclass
class NoiseTolerantLearningConfig:
    sample_count: int           # Number of examples (required)
    
    # Rejection thresholds
    cutoff_spread: int = 3      # Max std dev for acceptance
    cutoff_fit: float = 0.05    # Min p-value for goodness-of-fit
    
    # Candidate spaces
    max_offset: int = 1000      # Max |b| to consider
    max_denominator: int = 100  # Max denominator for fractions
    
    # Prior parameters
    expected_depth: int = 5     # Expected Stern-Brocot depth
    
    # Confidence intervals
    a_alpha: float = 0.025      # Two-tailed alpha for a (95% CI)
    b_alpha: float = 0.025      # Two-tailed alpha for b (95% CI)
```

**Tuning guidelines**:
- **max_denominator**: Increase for more precise ratios (slower), decrease for simpler (faster)
- **max_offset**: Set to slightly larger than max(screen dimensions)
- **expected_depth**: Lower values favor simpler fractions (1/2, 1/3), higher allows more complex
- **cutoff_spread**: Increase to be more tolerant of noise, decrease for stricter fit requirements

---

## Comparison of Methods

| Feature | Simple | Heuristic | Bayesian |
|---------|--------|-----------|----------|
| **Handles inconsistent data** | ✗ | ✗ | ✓ |
| **Uncertainty quantification** | ✗ | Heuristic | ✓ (Principled) |
| **Multiple candidates** | ✗ | ✓ | ✓ |
| **Noise tolerance** | ✗ | ✗ | ✓ |
| **Speed** | Very fast | Fast | Moderate |
| **Use case** | Perfect data | Quick prototyping | Production |

---

## Implementation Details

### Parallel Processing

For large template sets (>100 templates), learning can be parallelized:

```python
if len(templates) >= 100:
    with ProcessPool() as pool:
        candidates = pool.map(learn_one_template, templates)
else:
    candidates = [learn_one_template(t) for t in templates]
```

### Numerical Stability

**Problem**: GLM fitting can fail when data is perfect (zero residuals)

**Solution**: Add tiny noise to prevent perfect separation:
```python
x_noise = np.random.randn(len(x)) * 1e-5
y_noise = np.random.randn(len(y)) * 1e-5
x_smudged = x + x_noise
y_smudged = y + y_noise
```

**Problem**: Very small/large parameter values cause numerical issues

**Solution**: Reject templates with extreme parameters or residuals

### Rationalization

Floating-point parameters are converted to rationals:

```python
# Float result from GLM
a_float = 0.333333...

# Convert to fraction with bounded denominator
a_rational = Rational(a_float).limit_denominator(max_denominator=100)
# => 1/3
```

---

## Integration with Pipeline

```python
def run_mockdown(examples):
    # 1. Instantiation
    templates = instantiate(examples)
    
    # 2. Learning
    config = NoiseTolerantLearningConfig(
        sample_count=len(examples),
        max_offset=max(ex.width, ex.height for ex in examples) + 10
    )
    learner = NoiseTolerantLearning(templates, examples, config)
    candidates = learner.learn()  # List[List[ConstraintCandidate]]
    
    # Flatten candidates
    all_candidates = [c for template_cands in candidates for c in template_cands]
    
    # 3. Pruning (next phase)
    pruned = prune(all_candidates, examples)
    
    return pruned
```

---

## Debugging and Validation

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('mockdown.learning')
```

**Output includes**:
- Accepted/rejected templates with reasons
- Confidence intervals for each template
- Candidate scores and rankings
- Data for each template

### Common Issues

**Too many candidates per template**:
- Confidence intervals are too wide (not enough data)
- Solution: Get more examples or tighten alpha parameters

**All templates rejected**:
- Data is too noisy (residuals > cutoff_spread)
- Solution: Increase cutoff_spread or clean data

**Poor parameter estimates**:
- Prior is too strong (overrides data)
- Solution: Adjust expected_depth or increase number of examples

---

## Summary

Bayesian parameter learning in Mockdown:

✓ **Input**: Constraint templates with unknown parameters + layout examples  
✓ **Output**: Constraint candidates with learned parameters + confidence scores  
✓ **Key algorithm**: Constrained GLM fitting + Bayesian posterior computation  
✓ **Three methods**: Simple (perfect data), Heuristic (scoring), Bayesian (robust)  

✓ **Bayesian advantages**:
  - Handles inconsistent/noisy data gracefully
  - Provides uncertainty quantification through multiple candidates
  - Principled statistical approach with priors
  - Rejection criteria filter poor-fitting templates

✓ **Key innovations**:
  - Extended Farey sequence for fraction candidates
  - Stern-Brocot depth prior for simplicity bias
  - Constrained GLM for enforcing constraint forms
  - Per-template rejection based on goodness-of-fit

This learning phase bridges template instantiation (form) and pruning (selection), providing the statistical foundation for robust constraint inference from examples.

