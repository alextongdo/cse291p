# Mockdown Reimplementation

## Summary

The goal of this summary is to perform a detailed analysis on the Mockdown codebase so that we can gain an in-depth understanding to re-implement it.

### Mockdown

Mockdown is a tool that synthesizes contraint-based visual layouts from examples.

Specifically, given a hierarchial layout JSON that can be mined from a website's HTML, images, or direct-manipulation editor like Figma, Mockdown aims to generate *layout constraints* that generalize to unseen screen sizes.

For example, a hierarchial layout JSON might look like:
```json
{
  "name": "root",
  "rect": [0, 0, 1200, 800],
  "children": [
    {
      "name": "header",
      "rect": [0, 0, 1200, 80],
      "children": []
    },
    {
      "name": "sidebar",
      "rect": [0, 80, 250, 800],
      "children": []
    },
    {
      "name": "main",
      "rect": [250, 80, 1200, 800],
      "children": []
    }
  ]
}
```
> Note that this describes a 1200 x 800 webpage, with a 80 height header and 250 width sidebar.

With multiple examples, the complete layout constraints synthesized by Mockdown might look like:

- `header.height = 80`
- `sidebar.width = 250`
- `sidebar.top = header.bottom + 0`
- `main.top = header.bottom + 0`
- `main.left = sidebar.right + 0`

In general, these constraints always conform to the equation $y=a\cdot x+b$ where $x$, $y$ are anchors like `header.height` and $a$, $b$ are numeric constants.

Mockdown's pipeline is broken down into two major phases: **local inference** and **global inference**.

#### Local Inference

The goal of local inference is to generate a set of candidate constraints matching the provided examples.

In general, all constraints are instances of the template $y=a\cdot x+b$.

However, some constraints are considered ill-formed, such as `sidebar.left = a * main.right` or `sidebar.left = main.width + b`. This is because edge ratios and edge-width relations are not considered realistic and discarded.

> Perhaps we can extend these equations to work with something more similar to CSS flexbox. For example, a child width in a row flexbox with 3 children is equal to `(1/3 * parent.width) - (2 * gap)`.

Another optimization used to prune the set of candidate constraints is the **visibility graph**. Intuitively, components of the UI typically are placed in relation to their immediate parents and neigbors. So any constraints where the pair of components are not parent-child or sibling-sibling are discarded. 

Additionally, any constraints where an uninterrupted line (not passing through any other anchors) cannot be drawn between the two anchors is discarded.

All pairs of anchors $(x, y)$ that survive the 3 pruning rules above become the constraint sketches like `sidebar.right = a * main.left + b`. Note that while the framework allows for multiple unknowns $a$ and $b$, in practice the "well-formed" sketches only contain a single unknown.

The final step to infer the unknown parameters $a$ and $b$ is **Bayseian parameter inference**.

Starting from a set of constraint sketches and a set of examples, the goal is output a set of candidate constraints where each constraint instantiates a sketch `sidebar.right = main.left + b` and *approximately* matches the examples.

Each example maps an anchor to a rational value (`sidebar.right = 250`) and can be mined from the hierarchial layout JSON. These can be thought of as locations for each anchor.

The approximation is necessary because the data (examples) may be noisy when mined from an image. In one example, we may see `sidebar.right = 250.3` but another might have `sidebar.right = 249.9`. Even with those examples, we wouldn't want to invalidate `sidebar.right = 250` as a constraint.

The intuitive way to approximately infer `250` when instantiating `sidebar.right = ?` is to minimize the mean square error (linear regression) between the line $y=a\cdot x+b$ (in our case `sidebar.right = b`) and the examples. However, this may not produce *simple* values like 250. In the `sidebar.right = ?` example, linear regression would infer `sidebar.right = 250.1`.

Instead, *Bayesian linear regression* maximizes $P(b | \text{examples}) \propto P(b) \cdot P(\text{examples} | b)$.

Because the noise is expected to be Gaussian, $P(\text{examples} | b) \propto \exp(-\text{mse}(b, \text{examples}))$ so we can maximize this exponential which is equivalent to minimizing MSE.

$P(b)$ is a prior we can define to give preference to simpler parameters. For multiplicative values $P(a)$, the paper uses the *Stern-Brocot depth*, which is a measure of the complexity of a rational number. For additive values $P(b)$, the probability is uniform over all integer values and zero on non-integer values. In practice, these integers are finite because it first uses linear regression to get a best fit and a confidence interval. It then only considers the integers within that finite interval.

```python
def bayesian_parameter_inference(sketch, examples):
    # This is constrained because in practice, either a or b is unknown, not both
    (a, b), mse, confidence_interval = constrained_linear_regression(sketch, examples)
    if mse > threshold:
        # Sketch rejected due to high MSE
        return []
    scored_params = []
    potential_params_from_prior = get_parameter_space(sketch, (a, b))
    for (a, b) in potential_params_from_prior:
        if is_in_interval((a, b), confidence_interval):
            # P(a) or P(b)
            prior = calculate_prior((a, b), sketch)
            # P(examples | a) or P(examples | b)
            likelihood = calculate_likelihood((a, b), sketch, examples)
            # P(a | examples) or P(b | examples)
            posterior = prior * likelihood
            # b or a
            scored_params.append((a, posterior))
    return scored_params

def get_parameter_space(sketch, (a, b)):
  """Returns plausible 'simple' parameters near the complex linear regression parameters."""
  pass
```

#### Global Inference

After local inference, we have a set of candidate (potentially conflicting and scored by likelihood) but complete constraints. The goal with global inference is to select the maximal satisfiable subset that across multiple test screen sizes (to make sure it generalizes). 

To encode the MaxSMT problem, each constraint gets a boolean control variable which represents if it's included in the subset or not. This boolean has a weight according to the score, so we prefer simpler constraints.

Each pair of anchor $x$ and screen size (w_j, h_j) gets a rational number variable $x_j$ that represents the placement/location of the anchor under this screen size.

The MaxSMT formula is encoded with all of the following formulas anded together:
- for each screen size, $\text{root.width}_j = w_j~\wedge \text{root.height}_j = h_j$: the root size must match the screen size.
- for each constraint $c_i$ and screen size $j$, $b_i \Rightarrow c^j_i$: the constraint with each anchor replaced by its location $x_j$ under the screen size. It is controlled by a boolean to allow the SMT to turn off this constraint if it is conflicting with others.
- domain specific facts like $x_j \geq 0$ and $\text{x.width}_j=\text{x.right}_j-\text{x.left}_j$

The solution given by the MaxSMT solver can then be converted to constraints by taking the set of all constraints whose corresponding control variables are set to true

While this formula works well for small layouts, it is too complex with many anchors/UI elements. To still compute this, the paper decomposes global MaxSMT query into smaller queries which...?

```python
# candidate_constraints: list of complete constraints c_1, c_2, ...
# test_dims: list of screen sizes [(w, h)]
# score: dict mapping constraint c_i -> score from local inference
def synthesize_hierarchial(candidate_constraints, test_dims):

    # root contains root.name, root.rect, and root.children
    worklist = [(root, test_dims)]
    max_satisfiable_constraints = set()

    while worklist:
        # 'focus' is the parent view we're solving for
        # 'dims_f' is the list of screen sizes to test for it
        focus_view, focus_dims = worklist.pop()

        # restrict to only constraints that define the layout of focus_view's *immediate children*.
        relevant_constraints = restrict(focus_view, candidate_constraints)

        # run the MaxSMT solver to find the best subset that works for all 'focus_dims'.
        selected_constraints = select(
            relevant_constraints,
            focus_view,
            focus_dims,
            scores
        )
        max_satisfiable_constraints.update(selected_constraints)

        for child_view in focus_view.children:
            child_dims = calculate_dims(
                focus_view,
                focus_dims,
                child_view,
                max_satisfiable_constraints
            )
            worklist.append((child_view, child_dims))
    return max_satisfiable_constraints
```

The goal of calculate_dims is to return a list of test dimensions that the **child UI element** must generalize to. However note that this is dependent on the parent UI element, because if the parent generalizes for `[100, 150, 300]`, the child must generalize to appropriate dimensions. If the child is approximately 1/3 of the size of the parent, it might need to generalize `[33, 50, 100]`. To accomplish this, `calculate_dims` creates a MaxSMT query that calculates the minimal and maxmimal size of the child UI element, given the `max_satisfiable_constraints` which link the child_view's dimensions all the way back to the parent's dimensions.