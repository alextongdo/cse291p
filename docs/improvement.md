## Current Mockdown system.

Mockdown currently performs two steps to synthesize layouts.

1. Local inference.

Abstracting away the parameter inference and etc, the high level overview of local inference is that:

First, they assume that all the layout examples are *isomorphic*, i.e. have the same hierarchial structure. Then, for **one of** the examples, they generate a bunch of *incomplete* layout constraint sketches from the *single* example (since the hierarchy is the same for all examples). These constraint sketches still incorporate information from the other examples, however, because the visibility matrix (visibility detection) is computed for *each* example and then unioned together.

Then, the constraint sketches are passed through Bayesian parameter inference, which looks at **all of the examples** at once to determine the constants for the constraint sketches. This produces a set of complete layout constraints.

2. Global inference.

The goal is now to select the maximally scoring layout constraints that do not conflict with each other on a set of different test screen sizes (user-specificed range). This is inefficient when done for every view's constraints at once, so the MaxSMT problem is broken down into subproblems where only the constraints involving a certain view and the view's children are solved at once.

## Improvement over Mockdown.

Now, I want to extend Mockdown be able to synthesize *structurally different* layouts, i.e. a layout that has 1 column under a certain range of screen sizes, 2 columns under larger screen sizes, etc.
This means that the initial assumption of *isomorphism* no longer applies.

Naive method: The easiest naive method to do this would be analyze the example and figure out which ones are isomorphic sets. These isomorphic sets can then be individually solved with Mockdown, resulting in a layout per isomorphic set which we can apply conditionally. We'd also need to select a screen size boundary from the original examples to apply them.

- Pros: Easy
- Cons: We may only have 1 example for some isomorphic sets; we aren't making use of any invariant constraints across isomorphic sets, such as a view maintaning the same wdith in different columns.

Better method: If we assume that the "name" key in the examples are unique for each view, we can use this to recognize which views are the same ones, even under structurally different layouts. 

We would still need to figure out the isomorphic sets. For each isomorphic set, we will generate a set of *incomplete* layout constraint sketches and union all the sketches. Then we do Bayseian parameter inference looking at every example, and look at the clustering of values to determine if each sketch has a conditional variant or not. For each cluster, if a majority of the examples it explains belongs to one isomorphic set, we know that cluster should be applied for that isomorphic set.

```
Sketch: sidebar.left = parent.left + b
Inference: Finds two different clusters at b=20 (for set_A) and b=200 (for set_B).
Output: [set_A] sidebar.left = parent.left + 20 and [set_B] sidebar.left = parent.left + 200
```

When we solve the MaxSMT problem, we will conjunct *all* the conditional and global constraints together, except we make it so that the each isomorphic set *implies* its conditional constraints. This makes the conditional constraints vaccously true when the MaxSMT solver is not solving for a corresponding screen size.

**How the Single SMT Query Works**

Let's break down the logic. Remember, the MaxSMT solver's job is to pick the highest-scoring set of constraints that doesn't cause a contradiction.

We give it:
- A pool of candidate constraints, each with a boolean "on/off" variable: $b_{\text{global}_1}, b_{\text{setA}_1}, b_{\text{setB}_1}$
- A set of test dimensions for each layout: `dims_A` (small sizes) and `dims_B` (large sizes).

The single logical formula we feed to the solver is a giant conjunction (an "AND" list) of rules. Here's what those rules look like in plain English:

Rule Block A (for `dims_A`): "FOR ALL screen sizes in `dims_A`:
- IF you turn on $b_{\text{global}_1}$ its constraint MUST be satisfied.
- IF you turn on $b_{\text{setA}_1}$ its constraint MUST be satisfied.
- IF you turn on $b_{\text{setB}_1}$, I DON'T CARE." (It is vacuously true).

... same thing for rule block A but swap `setA` and `setB`.

The Objective: "NOW... find the combination of $b_{\text{global}_1}, b_{\text{setA}_1}, b_{\text{setB}_1}$, etc. that has the highest total score AND makes all of the above rules true."