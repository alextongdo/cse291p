import warnings
from collections import defaultdict
from fractions import Fraction
from functools import lru_cache

import numpy as np
import scipy.stats as st
import statsmodels.api as sm
import statsmodels.tools.sm_exceptions as sm_exc

from src.config import ConditionalLearningConfig, LearningConfig
from src.logging import get_logger
from src.types import LinearConstraint, View

logger = get_logger(__name__)


class TemplateBayesianLinearModel:
    """
    Bayesian learning for a single constraint template.
    Fits GLM with form constraints, computes confidence intervals,
    filters candidates, and scores them using Bayesian inference.
    """

    def __init__(
        self,
        template: LinearConstraint,
        config: LearningConfig,
        y_data: np.ndarray,
        x_data: np.ndarray | None = None,
    ):
        self.template = template
        self.config = config
        self.y_data = y_data
        self.x_data = x_data

        # Determine constraint form
        self.is_constant_form = template.x is None
        self.is_mul_only_form = template.x is not None and template.b == 0.0
        self.is_add_only_form = template.x is not None and template.a == 1.0

        # Fit the model
        self._fit()

    def _fit(self):
        """Fit constrained GLM to the data."""

        y_data = self.y_data.copy()

        if self.is_constant_form:
            # For constants, x is dummy zeros
            x_data = np.zeros(len(self.y_data))
        else:
            x_data = self.x_data.copy()

        assert len(x_data) == len(y_data)

        # Add intercept column
        x_with_const = sm.add_constant(x_data, has_constant="add")

        # Handle single example case: add synthetic data point
        if len(y_data) == 1:
            if self.is_constant_form:
                # Duplicate the point
                x_with_const = np.vstack([x_with_const, [1, 0]])
                y_data = np.append(y_data, y_data[0])
            elif self.is_mul_only_form:
                # Add origin point for y = a*x
                x_with_const = np.vstack([x_with_const, [1, 0]])
                y_data = np.append(y_data, 0)
            elif self.is_add_only_form:
                # Preserve computed offset
                x_with_const = np.vstack([x_with_const, [1, 0]])
                y_data = np.append(y_data, y_data[0] - x_data[0])

        # Add tiny noise to avoid perfect separation
        x_smudged, y_smudged = self.smudge_data(x_with_const, y_data)

        # Fit GLM with form constraints
        # Note: statsmodels is finicky, may need retries
        max_retries = 10
        for attempt in range(max_retries):
            try:
                model = sm.GLM(y_smudged, x_smudged)

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")

                    if self.is_constant_form:
                        # y = b, force a = 0
                        # Constraint: (0*b) + (1*a) = 0
                        self.fit = model.fit_constrained(((0, 1), 0))
                    elif self.is_mul_only_form:
                        # y = a*x, force b = 0
                        # Constraint: (1*b) + (0*a) = 0
                        self.fit = model.fit_constrained(((1, 0), 0))
                    elif self.is_add_only_form:
                        # y = x + b, force a = 1
                        # Constraint: (0*b) + (1*a) = 1
                        self.fit = model.fit_constrained(((0, 1), 1))
                    else:
                        assert (
                            False  # noqa: B011
                        ), "Mockdown in practice only learns a or b, not both."
                        # Full form: y = a*x + b
                        self.fit = model.fit()

                self.model = model
                break

            except sm_exc.PerfectSeparationError:
                # Numerical issue, try again with different noise
                if attempt < max_retries - 1:
                    x_smudged, y_smudged = TemplateBayesianLinearModel.smudge_data(
                        x_with_const, y_data
                    )
                    continue
                else:
                    raise

    def should_reject(self) -> bool:
        """
        Check if template should be rejected based on fit quality.

        Rejection criteria:
        1. No x variance but high y variance (can't explain y)
        2. No y variance but high x variance (y doesn't depend on x)
        3. High residual variance (poor fit)
        """
        x_data = np.zeros(len(self.y_data)) if self.is_constant_form else self.x_data
        y_data = self.y_data

        # Check 1: No x variance but y varies
        if np.var(x_data) == 0 and np.std(y_data) >= self.config.std_threshold:
            return True

        # Check 2: No y variance but x varies
        if np.var(y_data) == 0 and np.std(x_data) >= self.config.std_threshold:
            return True

        # Check 3: High residuals (poor fit)
        return np.std(self.fit.resid_response) > self.config.std_threshold

    def get_confidence_intervals(
        self,
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """
        Get confidence intervals for parameters a and b.

        Note: We compute confidence intervals separately for a and b
        using their respective alpha values, following the original Mockdown.

        Returns:
            ((a_lower, a_upper), (b_lower, b_upper))
        """
        # Get confidence interval for 'a' using a_alpha
        # Row 1 = coefficient = a
        a_ci = self.fit.conf_int(alpha=self.config.a_alpha / 2)[1]
        a_lower, a_upper = a_ci[0], a_ci[1]

        # Get confidence interval for 'b' using b_alpha
        # Row 0 = intercept = b
        b_ci = self.fit.conf_int(alpha=self.config.b_alpha / 2)[0]
        b_lower, b_upper = b_ci[0], b_ci[1]

        return (a_lower, a_upper), (b_lower, b_upper)

    def filter_candidates(self) -> list[tuple[Fraction, int]]:
        """
        Find candidate parameter values within confidence intervals.

        Returns:
            List of (a, b) tuples where a is Fraction and b is int
        """
        (a_lower, a_upper), (b_lower, b_upper) = self.get_confidence_intervals()

        # Find a candidates in CI
        a_space = TemplateBayesianLinearModel.get_a_space(self.config.max_denominator)
        a_mask = (a_space >= a_lower) & (a_space <= a_upper)
        a_candidates = a_space[a_mask]

        # Handle edge case: CI is between candidates
        if len(a_candidates) == 0:
            a_center = (a_lower + a_upper) / 2
            idx = np.searchsorted(a_space, a_center)
            a_candidates = np.array(
                [
                    a_space[max(0, idx - 1)],
                    a_space[min(idx, len(a_space) - 1)],
                ],
                dtype=object,
            )

        # Find b candidates in CI
        b_space = TemplateBayesianLinearModel.get_b_space(self.config.max_offset)
        b_mask = (b_space >= b_lower) & (b_space <= b_upper)
        b_candidates = b_space[b_mask]

        # Handle edge case
        if len(b_candidates) == 0:
            b_center = (b_lower + b_upper) / 2
            idx = np.searchsorted(b_space, b_center)
            b_candidates = np.array(
                [
                    b_space[max(0, idx - 1)],
                    b_space[min(idx, len(b_space) - 1)],
                ]
            )

        # Cartesian product (keep Fraction objects for a, int for b)
        candidates = [(a, int(b)) for a in a_candidates for b in b_candidates]

        return candidates

    def likelihood_score(self, a: Fraction | int, b: int) -> float:
        """
        Compute log-likelihood of data given parameters (a, b).

        Uses GLM log-likelihood function.
        """
        # Note: GLM expects (intercept, coefficient) = (b, a)
        # GLM will auto-convert Fraction to float
        # Suppress warnings from perfect separation in GLM
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return self.model.loglike((float(b), float(a)))

    def prior_score(self, a: Fraction | int) -> float:
        """
        Compute prior probability for parameter 'a'.

        Based on Stern-Brocot depth (favors simpler fractions).
        """
        # Find index of this a in a_space
        a_space = TemplateBayesianLinearModel.get_a_space(self.config.max_denominator)
        idx = np.searchsorted(a_space, a)

        # Get prior from pre-computed distribution
        a_prior = TemplateBayesianLinearModel.get_a_prior(
            self.config.max_denominator, self.config.expected_sb_depth
        )
        return a_prior[idx]

    def learn(self) -> list[LinearConstraint]:
        """
        Perform Bayesian inference to learn constraint parameters.

        Returns:
            List of constraint candidates with posterior scores
        """
        if self.should_reject():
            return []

        # Get candidates in confidence intervals (list of (a, b) tuples)
        candidates = self.filter_candidates()

        if len(candidates) == 0:
            return []

        # Compute likelihood for each candidate
        log_likelihoods = np.array([self.likelihood_score(a, b) for a, b in candidates])
        likelihoods = np.exp(log_likelihoods)

        # Normalize likelihood
        likelihood_sum = likelihoods.sum()
        if likelihood_sum > 0:
            likelihoods /= likelihood_sum
        else:
            # If all likelihoods are zero, use uniform distribution
            likelihoods = np.ones_like(likelihoods) / len(likelihoods)

        # Compute prior for each candidate
        priors = np.array([self.prior_score(a) for a, b in candidates])

        # Normalize prior
        priors /= priors.sum()

        # Compute posterior: Prior × Likelihood
        posteriors = likelihoods * priors

        # No need to normalize posteriors probabilities to sum
        # to 1, since only the relative ranking matters for score

        results = []
        for (a, b), score in zip(candidates, posteriors, strict=True):
            results.append(
                LinearConstraint(
                    y=self.template.y,
                    x=self.template.x,
                    a=a,
                    b=b,
                    score=float(score),
                )
            )
        return sorted(results, key=lambda c: -c.score)

    @staticmethod
    def smudge_data(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Add tiny noise to avoid perfect separation in GLM."""
        # Generate 1D noise for x and broadcast across columns
        x_noise = np.random.randn(len(x)) * 1e-5
        x_noise -= x_noise.mean()  # ALEX ADDDED
        # Broadcasting: add noise to each row
        x_smudged = x + x_noise[:, np.newaxis]

        # Generate noise for y
        y_noise = np.random.randn(len(y)) * 1e-5
        y_noise -= y_noise.mean()  # ALEX ADDDED
        y_smudged = y + y_noise

        return x_smudged, y_smudged

    @staticmethod
    @lru_cache(maxsize=1)
    def get_a_space(max_denominator: int) -> np.ndarray:
        """Search space for all possible values of a in y = a * x + b."""

        def _farey_sequence(n: int) -> np.ndarray:
            """
            Generate Farey sequence: all fractions p/q with 0 ≤ p ≤ q ≤ n.
            Example n = 5: [0/1, 1/5, 1/4, 1/3, 2/5, 1/2, 3/5, 2/3, 3/4, 4/5, 1/1]
            """
            fractions = [Fraction(0, 1)]
            fractions.extend(
                sorted(
                    {Fraction(m, k) for k in range(1, n + 1) for m in range(1, k + 1)}
                )
            )
            return np.array(fractions, dtype=object)

        # Farey sequence only contains fractions less than 1.
        proper_fractions = _farey_sequence(max_denominator)
        # But a can be larger than 1, so also consider all the reciprocal fractions
        reciprocals = [
            Fraction(1) / a for a in reversed(proper_fractions[1:-1])
        ]  # except 1/0 and 1/1
        return np.append(proper_fractions, reciprocals)

    @staticmethod
    @lru_cache(maxsize=1)
    def get_b_space(max_offset: int):
        """Search space for all possible values of b in y = a * x + b."""

        def _z_ball(center: float = 0, radius: float = 1000) -> np.ndarray:
            """
            Integer ball: all integers in [center - radius, center + radius).
            Example: z_ball(0, 1000) => [-1000, -999, ..., 0, 1, ..., 999]
            """
            return np.arange(
                int(np.ceil(center - radius)), int(np.floor(center + radius)), dtype=int
            )

        return _z_ball(0, max_offset)

    @staticmethod
    @lru_cache(maxsize=1)
    def get_a_prior(max_denominator: int, expected_sb_depth: int):
        """
        Prior distribution over 'a' candidates based on Stern-Brocot depth.
        Uses beta-binomial distribution favoring expected_sb_depth.
        """

        def _continued_fraction(fraction: Fraction) -> list[int]:
            """
            Compute continued fraction expansion of a rational number.
            Example: 2/5 = [0; 2, 2] means 0 + 1/(2 + 1/2)
            """
            n1, n2 = fraction.numerator, fraction.denominator
            terms = []
            while n2:
                n1, (term, n2) = n2, divmod(n1, n2)
                terms.append(term)
            return terms

        def _sb_depth(fraction: Fraction) -> int:
            """
            Stern-Brocot depth = sum of continued fraction terms.
            Measures fraction complexity/simplicity:
            - 1/2 = [0; 2]        => depth = 2  (simple!)
            - 2/5 = [0; 2, 2]     => depth = 4
            - 47/83 = [0; 1,1,3,4,2] => depth = 11 (complex!)
            """
            return sum(_continued_fraction(fraction))

        max_d, exp_d = max_denominator, expected_sb_depth
        n = max_d
        alpha = exp_d + 1
        beta = (max_d - exp_d) + 1

        # Compute sb_depth for each candidate in a_space
        sb_depths = np.array(
            [
                _sb_depth(a)
                for a in TemplateBayesianLinearModel.get_a_space(max_denominator)
            ]
        )

        # Histogram of depths (for normalization)
        sb_depth_hist, _ = np.histogram(sb_depths, bins=max_d + 1)

        # Beta-binomial probabilities for each depth level
        betabin = np.array(
            [st.betabinom.pmf(k, n, alpha, beta) for k in range(max_d + 1)]
        )

        # Assign prior: P(depth_k) / count(fractions at depth_k)
        # This makes it uniform within each depth level
        prior = betabin[sb_depths] / (sb_depth_hist[sb_depths] + 1e-10)
        return prior


class BayesianLearning:
    def __init__(
        self,
        examples: list[View],
        config: LearningConfig | None = None,
        seed: int | None = None,
    ):
        self.examples = examples
        if config is None:
            max_dim = max(max(root.width, root.height) for root in examples)
            self.config = LearningConfig(max_offset=int(max_dim) + 10)
        else:
            self.config = config

        if seed is not None:
            np.random.seed(seed)

        # Pre-compute anchor data map for all examples
        anchor_to_data_map: dict[str, list[float]] = defaultdict(list)
        for example in self.examples:
            for view in example._flattened_views_in_subtree:
                anchor_to_data_map[f"{view.name}.width"].append(view.width)
                anchor_to_data_map[f"{view.name}.height"].append(view.height)
                anchor_to_data_map[f"{view.name}.left"].append(view.left)
                anchor_to_data_map[f"{view.name}.right"].append(view.right)
                anchor_to_data_map[f"{view.name}.top"].append(view.top)
                anchor_to_data_map[f"{view.name}.bottom"].append(view.bottom)
                anchor_to_data_map[f"{view.name}.center_x"].append(view.center_x)
                anchor_to_data_map[f"{view.name}.center_y"].append(view.center_y)
        self.anchor_to_data_map = anchor_to_data_map

    def learn(self, templates: list[LinearConstraint]) -> list[LinearConstraint]:
        """
        Main interface for Bayesian parameter learning.

        Args:
            templates: List of constraint templates with unknown parameters

        Returns:
            List of learned constraints with scores
        """

        results = []
        for template in templates:
            # logger.debug(f"Doing Bayesian learning for {repr(template)}")
            # Extract anchor values data for the template from all examples.
            y_data = np.array(
                self.anchor_to_data_map[f"{template.y.view.name}.{template.y.type}"],
                dtype=float,
            )
            if template.x is None:
                x_data = None
            else:
                x_data = np.array(
                    self.anchor_to_data_map[
                        f"{template.x.view.name}.{template.x.type}"
                    ],
                    dtype=float,
                )

            # Learn parameters for this template
            model = TemplateBayesianLinearModel(
                template=template, config=self.config, y_data=y_data, x_data=x_data
            )
            candidates = model.learn()
            # if len(candidates) == 0:
            #     logger.debug("Learned 0 candidates")
            # for cand in candidates:
            #     logger.debug(f"Learned {repr(cand)}")
            results.extend(candidates)

        return results


class ConditionalBayesianLearning:
    """
    Bayesian learning with clustering-based parameter mode detection.

    Key innovation: Examples within each structural set are clustered by their
    observed parameter values before learning. This handles cases where the same
    structural set has multiple parameter modes (e.g., margin=10 for some examples,
    margin=50 for others).
    """

    def __init__(
        self,
        examples: list[View],
        config: ConditionalLearningConfig | None = None,
        seed: int | None = None,
    ):
        self.examples = examples
        if config is None:
            max_dim = max(max(root.width, root.height) for root in examples)
            self.config = ConditionalLearningConfig(max_offset=int(max_dim) + 10)
        else:
            self.config = config

        if seed is not None:
            np.random.seed(seed)

        # Pre-compute anchor data map for all examples
        anchor_to_data_map: dict[str, list[float]] = defaultdict(list)
        for example in self.examples:
            for view in example._flattened_views_in_subtree:
                anchor_to_data_map[f"{view.name}.width"].append(view.width)
                anchor_to_data_map[f"{view.name}.height"].append(view.height)
                anchor_to_data_map[f"{view.name}.left"].append(view.left)
                anchor_to_data_map[f"{view.name}.right"].append(view.right)
                anchor_to_data_map[f"{view.name}.top"].append(view.top)
                anchor_to_data_map[f"{view.name}.bottom"].append(view.bottom)
                anchor_to_data_map[f"{view.name}.center_x"].append(view.center_x)
                anchor_to_data_map[f"{view.name}.center_y"].append(view.center_y)
        self.anchor_to_data_map = anchor_to_data_map

    def _get_anchor_value(self, example_idx: int, anchor_key: str) -> float:
        """Get anchor value for a specific example."""
        return self.anchor_to_data_map[anchor_key][example_idx]

    def _cluster_template_examples(
        self,
        template: LinearConstraint,
        example_idxs: tuple[int, ...],
    ) -> list[list[int]]:
        """
        Cluster examples within a structural set based on observed parameter values.

        Args:
            template: The constraint template
            example_idxs: Indices of examples in this structural set

        Returns:
            List of clusters, where each cluster contains original example indices
        """
        y_key = f"{template.y.view.name}.{template.y.type}"
        y_values = [self._get_anchor_value(i, y_key) for i in example_idxs]

        is_constant_form = template.x is None
        is_mul_only_form = template.x is not None and template.b == 0.0
        is_add_only_form = template.x is not None and template.a == 1.0

        if is_constant_form:
            # Constant form: y = b → observed b = y
            observed = y_values
            observations = list(zip(observed, example_idxs, strict=True))
            clusters = cluster_by_observed_param(
                observations, b_threshold=self.config.b_cluster_threshold
            )
        elif is_mul_only_form:
            # Multiplicative form: y = a*x → observed a = y/x
            x_key = f"{template.x.view.name}.{template.x.type}"
            x_values = [self._get_anchor_value(i, x_key) for i in example_idxs]
            observed = [
                y / x if x != 0 else 0.0
                for y, x in zip(y_values, x_values, strict=True)
            ]
            observations = list(zip(observed, example_idxs, strict=True))
            clusters = cluster_by_observed_param(
                observations, a_threshold=self.config.a_cluster_threshold
            )
        elif is_add_only_form:
            # Additive form: y = x + b → observed b = y - x
            x_key = f"{template.x.view.name}.{template.x.type}"
            x_values = [self._get_anchor_value(i, x_key) for i in example_idxs]
            observed = [y - x for y, x in zip(y_values, x_values, strict=True)]
            observations = list(zip(observed, example_idxs, strict=True))
            clusters = cluster_by_observed_param(
                observations, b_threshold=self.config.b_cluster_threshold
            )
        else:
            raise NotImplementedError(
                "Mockdown in practice only learns a or b, not both."
            )

        if len(clusters) > 1:
            logger.debug(
                f"  Template {repr(template)} split into "
                f"{len(clusters)} clusters: {clusters}"
            )
            logger.debug(f"    Observations: {observations}")

        return clusters

    def learn(
        self,
        example_idxs_to_templates_map: dict[tuple, list[LinearConstraint]],
    ) -> dict[tuple[int, ...], list[LinearConstraint]]:
        """
        Perform Bayesian learning per structural set with clustering, then merge
        constraints across sets.

        For each template, examples are clustered by their observed parameter
        values before learning. This handles cases where the same structural set
        has multiple parameter modes (e.g., margin=10 for some, margin=50 for others).

        Args:
            example_idxs_to_templates_map:
                Maps example index tuples to their templates
                e.g., {(0, 1): [templates], (2, 3): [templates]}

        Returns:
            Dictionary mapping example index tuples to learned constraints:
            - (0, 1): constraints specific to examples 0, 1
            - (2, 3): constraints specific to examples 2, 3
            - (0, 1, 2, 3): constraints that apply to all (merged)
        """
        # Map cosntraints to examples they apply to
        constr_to_sets_map: dict[LinearConstraint, set[int]] = defaultdict(set)
        # Map constraints to their max score equivalents
        constr_to_max_score_map: dict[LinearConstraint, LinearConstraint] = {}

        for example_idxs, templates in example_idxs_to_templates_map.items():
            logger.debug(f"\n\nLearning for structural set {example_idxs}")

            for template in templates:
                # Cluster examples by observed parameter values
                clusters = self._cluster_template_examples(template, example_idxs)

                # Learn separately for each cluster
                for cluster_example_idxs in clusters:
                    cluster_examples = [self.examples[i] for i in cluster_example_idxs]
                    learned = BayesianLearning(
                        examples=cluster_examples, config=self.config
                    ).learn([template])

                    for constr in learned:
                        constr_to_sets_map[constr].update(cluster_example_idxs)
                        if (
                            constr not in constr_to_max_score_map
                            or constr.score > constr_to_max_score_map[constr].score
                        ):
                            constr_to_max_score_map[constr] = constr

        # Map examples to which constraints apply to them
        output: dict[tuple[int, ...], list[LinearConstraint]] = defaultdict(list)
        for constr, example_idxs_set in constr_to_sets_map.items():
            output[tuple(sorted(example_idxs_set))].append(
                constr_to_max_score_map[constr]
            )

        # Sanity check: no duplicate constraints in any list
        for constr_list in output.values():
            assert len(set(constr_list)) == len(constr_list)

        return dict(output)


def cluster_by_observed_param(
    observations: list[tuple[float, int]],
    a_threshold: float | None = None,
    b_threshold: float | None = None,
) -> list[list[int]]:
    """
    Cluster examples by their observed parameter values.
    Simple 1D greedy clustering. Exactly one threshold must be provided.

    Args:
        observations: List of (value, example_idx) tuples
        a_threshold: Relative threshold for ratios (e.g., 0.1 = 10% difference)
        b_threshold: Absolute threshold for offsets (e.g., 5 = |b1-b2| ≤ 5)

    Returns:
        List of clusters, where each cluster is a list of example indices

    Example:
        >>> cluster_by_observed_param(
        >>>     [(10, 0), (50, 1), (12, 2), (48, 3)], b_threshold=5
        >>> )
        [[0, 2], [1, 3]]  # examples with values [10, 12] and [48, 50] grouped
    """
    if (a_threshold is None) == (b_threshold is None):
        raise ValueError("Exactly one of a_threshold or b_threshold must be provided")

    if len(observations) <= 1:
        return [[idx for _, idx in observations]]

    # Sort by value
    sorted_obs = sorted(observations, key=lambda x: x[0])

    # Greedy clustering: start new cluster when gap exceeds threshold
    clusters = [[sorted_obs[0][1]]]

    for i in range(1, len(sorted_obs)):
        curr_val, curr_idx = sorted_obs[i]
        prev_val, _ = sorted_obs[i - 1]

        if a_threshold is not None:
            # Relative distance for ratios
            avg_val = ((abs(curr_val) + abs(prev_val)) / 2) + 1e-10
            distance = abs(curr_val - prev_val) / avg_val
            threshold = a_threshold
        else:
            # Absolute distance for offsets
            distance = abs(curr_val - prev_val)
            threshold = b_threshold

        if distance <= threshold:
            clusters[-1].append(curr_idx)
        else:
            clusters.append([curr_idx])

    return clusters
