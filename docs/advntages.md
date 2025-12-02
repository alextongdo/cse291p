What are the advantages of my conditional Mockdown algorithm?

1. Automatic discovery of structurally similar examples.

2. Nothing else I guess?

- During bayesian learning, my conditional function just calls bayesian learning for each structural set, and then detects which ones are global / conditional.

- During MaxSMT, my conditional function also just calls hierarchial pruning for all the examples in a structural set.

Therefore, my method is akin to basically running the automatic discovery algorithm, and then running the original mockdown tool separately for each structural set found. Then by finding the intersection of the sets, we would obtain the same global constraints. This makes my conditional algorithm **not at all different** than just running the Mockdown tool a few times.


So what are my options for making my conditional algorithm better than just using the Mockdown tool multiple times? What information does the original Mockdown not leverage?

1. In the original Mockdown, the parameter learning is noise tolerant to a certain degree, but if you had like 
margin 10 and then margin 15, it would break (remove the constraint altogether). This is more suitable to an approach like conditional constraints, but this would require me to replace the Bayesian regression with some sort of clustering algorithm to learning that some examples give margin 10, and some give margin 15.

2. In the original Mockdown, if we just use the tool multiple times, noise tolerant learning does not apply for **global constraints**. For example, if in structural set A, there is margin = 10 and in structural set B, there is a margin = 11, it would not be recognized as a global constraint, since its not noise-tolerant.