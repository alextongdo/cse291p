"""
Bayesian Parameter Learning for Constraint Templates

Implements noise-tolerant Bayesian inference to learn constraint parameters
from multiple layout examples. Based on Mockdown's learning module.
"""

import warnings
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import scipy.stats as st
import statsmodels.api as sm
import statsmodels.tools.sm_exceptions as sm_exc

from src.types import LinearConstraint, View


# ============================================================
# Mathematical Utilities
# ============================================================

def continued_fraction(fraction: Fraction) -> List[int]:
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


def sb_depth(fraction: Fraction) -> int:
    """
    Stern-Brocot depth = sum of continued fraction terms.
    
    Measures fraction complexity/simplicity:
    - 1/2 = [0; 2]        => depth = 2  (simple!)
    - 2/5 = [0; 2, 2]     => depth = 4
    - 47/83 = [0; 1,1,3,4,2] => depth = 11 (complex!)
    """
    return sum(continued_fraction(fraction))


@lru_cache(maxsize=1)
def farey_sequence(n: int = 100) -> np.ndarray:
    """
    Generate Farey sequence F_n: all fractions p/q with 0 ≤ p ≤ q ≤ n.
    
    Example F_5: [0/1, 1/5, 1/4, 1/3, 2/5, 1/2, 3/5, 2/3, 3/4, 4/5, 1/1]
    """
    fractions = [Fraction(0, 1)]
    fractions.extend(sorted({
        Fraction(m, k)
        for k in range(1, n + 1)
        for m in range(1, k + 1)
    }))
    return np.array(fractions, dtype=object)


@lru_cache(maxsize=1)
def ext_farey(n: int = 100) -> np.ndarray:
    """
    Extended Farey sequence: F_n plus reciprocals of (1, n].
    
    Extends the range from [0, 1] to [0, n].
    Example: [0, 1/100, ..., 1/2, ..., 1, 2, 3, ..., 100]
    """
    f = farey_sequence(n)
    # Append reciprocals in reverse (excluding 0 and 1)
    reciprocals = [Fraction(1) / a for a in reversed(f[1:-1])]
    return np.append(f, reciprocals)


def z_ball(center: float = 0, radius: float = 1000) -> np.ndarray:
    """
    Integer ball: all integers in [center-radius, center+radius).
    
    Example: z_ball(0, 1000) => [-1000, -999, ..., 0, 1, ..., 999]
    """
    return np.arange(int(np.ceil(center - radius)), 
                     int(np.floor(center + radius)), 
                     dtype=int)


# ============================================================
# Configuration
# ============================================================

@dataclass(frozen=True)
class LearningConfig:
    """Configuration for Bayesian parameter learning."""
    
    # Number of examples
    sample_count: int
    
    # Rejection thresholds
    cutoff_spread: float = 3.0  # Max std dev for acceptance
    
    # Candidate spaces
    max_offset: int = 1000      # Max |b| to consider
    max_denominator: int = 100  # Max denominator for fractions
    
    # Prior parameters
    expected_depth: int = 5     # Expected Stern-Brocot depth
    
    # Confidence intervals (two-tailed alpha for 95% CI)
    a_alpha: float = 0.025
    b_alpha: float = 0.025
    
    @property
    @lru_cache(maxsize=1)
    def a_space(self) -> np.ndarray:
        """Full candidate space for 'a' parameter (ratios)."""
        return ext_farey(self.max_denominator)
    
    @property
    @lru_cache(maxsize=1)
    def b_space(self) -> np.ndarray:
        """Full candidate space for 'b' parameter (offsets)."""
        return z_ball(0, self.max_offset)
    
    @property
    @lru_cache(maxsize=1)
    def depth_prior(self) -> np.ndarray:
        """
        Prior distribution over 'a' candidates based on Stern-Brocot depth.
        
        Uses beta-binomial distribution favoring expected_depth.
        """
        max_d, exp_d = self.max_denominator, self.expected_depth
        n = max_d
        alpha = exp_d + 1
        beta = (max_d - exp_d) + 1
        
        # Compute depth for each candidate in a_space
        sb_depths = np.array([sb_depth(a) for a in self.a_space])
        
        # Histogram of depths (for normalization)
        sb_depth_hist, _ = np.histogram(sb_depths, bins=max_d + 1)
        
        # Beta-binomial probabilities for each depth level
        betabin = np.array([
            st.betabinom.pmf(k, n, alpha, beta) 
            for k in range(max_d + 1)
        ])
        
        # Assign prior: P(depth_k) / count(fractions at depth_k)
        # This makes it uniform within each depth level
        prior = betabin[sb_depths] / (sb_depth_hist[sb_depths] + 1e-10)
        return prior


# ============================================================
# Constraint Candidate
# ============================================================

@dataclass(order=True)
class ConstraintCandidate:
    """A learned constraint with its posterior probability score."""
    score: float
    constraint: LinearConstraint


# ============================================================
# Template Data Extraction
# ============================================================

def extract_template_data(
    template: LinearConstraint, 
    examples: List[View]
) -> pd.DataFrame:
    """
    Extract anchor values for a template from all examples.
    
    Returns:
        DataFrame with columns [y_name, x_name] or just [y_name] for constants
    """
    y_name = f"{template.y.view.name}.{template.y.type}"
    
    if template.x is None:
        # Constant form: y = b
        data = []
        for example in examples:
            # Find matching view in this example
            y_view = next(v for v in example._flattened_views_in_subtree 
                         if v.name == template.y.view.name)
            y_value = get_anchor_value(y_view, template.y.type)
            data.append([y_value])
        
        return pd.DataFrame(data, columns=[y_name])
    else:
        # Linear form: y = a*x + b
        x_name = f"{template.x.view.name}.{template.x.type}"
        data = []
        for example in examples:
            y_view = next(v for v in example._flattened_views_in_subtree 
                         if v.name == template.y.view.name)
            x_view = next(v for v in example._flattened_views_in_subtree 
                         if v.name == template.x.view.name)
            
            y_value = get_anchor_value(y_view, template.y.type)
            x_value = get_anchor_value(x_view, template.x.type)
            data.append([y_value, x_value])
        
        return pd.DataFrame(data, columns=[y_name, x_name])


def get_anchor_value(view: View, anchor_type: str) -> float:
    """Get the value of a specific anchor from a view."""
    left, top, right, bottom = view.rect
    
    if anchor_type == "left":
        return left
    elif anchor_type == "right":
        return right
    elif anchor_type == "top":
        return top
    elif anchor_type == "bottom":
        return bottom
    elif anchor_type == "width":
        return right - left
    elif anchor_type == "height":
        return bottom - top
    elif anchor_type == "center_x":
        return (left + right) / 2
    elif anchor_type == "center_y":
        return (top + bottom) / 2
    else:
        raise ValueError(f"Unknown anchor type: {anchor_type}")


# ============================================================
# Template Model (per-template learning)
# ============================================================

class TemplateModel:
    """
    Bayesian learning for a single constraint template.
    
    Fits GLM with form constraints, computes confidence intervals,
    filters candidates, and scores them using Bayesian inference.
    """
    
    def __init__(
        self,
        template: LinearConstraint,
        examples: List[View],
        config: LearningConfig
    ):
        self.template = template
        self.examples = examples
        self.config = config
        self.data = extract_template_data(template, examples)
        
        # Determine constraint form
        self.is_constant_form = (template.x is None)
        self.is_mul_only_form = (template.x is not None and template.b == 0.0)
        self.is_add_only_form = (template.x is not None and template.a == 1.0)
        
        # Fit the model
        self._fit_model()
    
    def _fit_model(self):
        """Fit constrained GLM to the data."""
        # Get x and y data
        y = self.data.iloc[:, 0]  # First column is y
        
        if self.is_constant_form:
            # For constants, x is dummy zeros
            x = pd.Series(np.zeros(len(y)), name='__dummy__')
        else:
            x = self.data.iloc[:, 1]  # Second column is x
        
        # Add intercept column
        x_with_const = sm.add_constant(x, has_constant='add')
        
        # Handle single example case: add synthetic data point
        if self.config.sample_count == 1:
            sc = self.config.sample_count
            if self.is_constant_form:
                # Duplicate the point
                x_with_const.loc[sc] = [1, 0]
                y.loc[sc] = y.loc[0]
            elif self.is_mul_only_form:
                # Add origin point for y = a*x
                x_with_const.loc[sc] = [1, 0]
                y.loc[sc] = 0
            elif self.is_add_only_form:
                # Preserve computed offset
                x_with_const.loc[sc] = [1, 0]
                y.loc[sc] = y.loc[0] - x.iloc[0]
        
        # Add tiny noise to avoid perfect separation
        x_smudged, y_smudged = self._smudge_data(x_with_const, y)
        
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
                        # Full form: y = a*x + b
                        self.fit = model.fit()
                
                self.model = model
                break
                
            except sm_exc.PerfectSeparationError:
                # Numerical issue, try again with different noise
                if attempt < max_retries - 1:
                    x_smudged, y_smudged = self._smudge_data(x_with_const, y)
                    continue
                else:
                    raise
    
    def _smudge_data(self, x: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
        """Add tiny noise to avoid perfect separation in GLM."""
        # Generate 1D noise and broadcast (matches original Mockdown behavior)
        x_noise = np.random.randn(len(x)) * 1e-5
        x_smudged = x.add(x_noise, axis=0)
        
        y_noise = np.random.randn(len(y)) * 1e-5
        y_smudged = y.add(y_noise, axis=0)
        
        return x_smudged, y_smudged
    
    def should_reject(self) -> bool:
        """
        Check if template should be rejected based on fit quality.
        
        Rejection criteria:
        1. No x variance but high y variance (can't explain y)
        2. No y variance but high x variance (y doesn't depend on x)
        3. High residual variance (poor fit)
        """
        if self.is_constant_form:
            x_data = pd.Series(np.zeros(len(self.data)))
        else:
            x_data = self.data.iloc[:, 1]
        
        y_data = self.data.iloc[:, 0]
        
        # Check 1: No x variance but y varies
        if np.var(x_data) == 0 and np.std(y_data) >= self.config.cutoff_spread:
            return True
        
        # Check 2: No y variance but x varies
        if np.var(y_data) == 0 and np.std(x_data) >= self.config.cutoff_spread:
            return True
        
        # Check 3: High residuals (poor fit)
        if np.std(self.fit.resid_response) > self.config.cutoff_spread:
            return True
        
        return False
    
    def get_confidence_intervals(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Get confidence intervals for parameters a and b.
        
        Note: We compute confidence intervals separately for a and b
        using their respective alpha values, following the original Mockdown.
        
        Returns:
            ((a_lower, a_upper), (b_lower, b_upper))
        """
        # Get confidence interval for 'a' using a_alpha
        # Row 1 = coefficient = a
        a_lower, a_upper = self.fit.conf_int(alpha=self.config.a_alpha).iloc[1]
        
        # Get confidence interval for 'b' using b_alpha
        # Row 0 = intercept = b
        b_lower, b_upper = self.fit.conf_int(alpha=self.config.b_alpha).iloc[0]
        
        return (a_lower, a_upper), (b_lower, b_upper)
    
    def filter_candidates(self) -> pd.DataFrame:
        """
        Find candidate parameter values within confidence intervals.
        
        Returns:
            DataFrame with columns ['a', 'b']
        """
        (a_lower, a_upper), (b_lower, b_upper) = self.get_confidence_intervals()
        
        # Find a candidates in CI
        a_space = self.config.a_space
        a_mask = (a_space >= a_lower) & (a_space <= a_upper)
        a_candidates = a_space[a_mask]
        
        # Handle edge case: CI is between candidates
        if len(a_candidates) == 0:
            a_center = (a_lower + a_upper) / 2
            idx = np.searchsorted(a_space, a_center)
            a_candidates = [a_space[max(0, idx - 1)], a_space[min(idx, len(a_space) - 1)]]
        
        # Find b candidates in CI
        b_space = self.config.b_space
        b_mask = (b_space >= b_lower) & (b_space <= b_upper)
        b_candidates = b_space[b_mask]
        
        # Handle edge case
        if len(b_candidates) == 0:
            b_center = (b_lower + b_upper) / 2
            idx = np.searchsorted(b_space, b_center)
            b_candidates = [b_space[max(0, idx - 1)], b_space[min(idx, len(b_space) - 1)]]
        
        # Cartesian product (keep Fraction objects for a, int for b)
        candidates = pd.DataFrame(
            [(a, b) for a in a_candidates for b in b_candidates],
            columns=['a', 'b']
        )
        
        return candidates
    
    def likelihood_score(self, a: Fraction | int, b: int) -> float:
        """
        Compute log-likelihood of data given parameters (a, b).
        
        Uses GLM log-likelihood function.
        """
        # Note: GLM expects (intercept, coefficient) = (b, a)
        # GLM will auto-convert Fraction to float
        return self.model.loglike((float(b), float(a)))
    
    def prior_score(self, a: Fraction | int) -> float:
        """
        Compute prior probability for parameter 'a'.
        
        Based on Stern-Brocot depth (favors simpler fractions).
        """
        # Find index of this a in a_space
        a_space = self.config.a_space
        idx = np.searchsorted(a_space, a)
        
        # Get prior from pre-computed distribution
        return self.config.depth_prior[idx]
    
    def learn(self) -> List[ConstraintCandidate]:
        """
        Perform Bayesian inference to learn constraint parameters.
        
        Returns:
            List of constraint candidates with posterior scores
        """
        if self.should_reject():
            return []
        
        # Get candidates in confidence intervals
        candidates = self.filter_candidates()
        
        if len(candidates) == 0:
            return []
        
        # Compute likelihood for each candidate
        candidates['log_likelihood'] = candidates.apply(
            lambda row: self.likelihood_score(row['a'], row['b']), 
            axis=1
        )
        candidates['likelihood'] = np.exp(candidates['log_likelihood'])
        
        # Normalize likelihood
        candidates['likelihood'] /= candidates['likelihood'].sum()
        
        # Compute prior for each candidate
        candidates['prior'] = candidates['a'].apply(self.prior_score)
        
        # Normalize prior
        candidates['prior'] /= candidates['prior'].sum()
        
        # Compute posterior: Prior × Likelihood
        candidates['posterior'] = candidates['likelihood'] * candidates['prior']
        
        # Normalize posterior
        candidates['posterior'] /= candidates['posterior'].sum()
        
        # Create ConstraintCandidate objects
        results = []
        for _, row in candidates.iterrows():
            # Create learned constraint with filled parameters
            # Keep a as Fraction, b as int for exact representation
            learned = LinearConstraint(
                y=self.template.y,
                x=self.template.x,
                a=row['a'],  # Fraction object
                b=int(row['b'])  # int object
            )
            
            results.append(ConstraintCandidate(
                score=row['posterior'],
                constraint=learned
            ))
        
        # Sort by descending score
        return sorted(results, key=lambda c: -c.score)


# ============================================================
# Main Learning Interface
# ============================================================

class BayesianLearning:
    """
    Bayesian parameter learning for all constraint templates.
    
    Main interface for the learning phase.
    """
    
    def __init__(
        self,
        templates: List[LinearConstraint],
        examples: List[View],
        config: Optional[LearningConfig] = None,
        random_seed: Optional[int] = 42
    ):
        self.templates = templates
        self.examples = examples
        
        # Set random seed for reproducibility
        if random_seed is not None:
            np.random.seed(random_seed)
        
        if config is None:
            # Auto-configure based on examples
            max_dim = max(
                max(view.width, view.height)
                for example in examples
                for view in example._flattened_views_in_subtree
            )
            config = LearningConfig(
                sample_count=len(examples),
                max_offset=int(max_dim) + 10
            )
        
        self.config = config
    
    def learn(self) -> List[List[ConstraintCandidate]]:
        """
        Learn parameters for all templates.
        
        Returns:
            List of candidate lists, one per template.
            Empty lists for rejected templates.
        """
        results = []
        
        for template in self.templates:
            model = TemplateModel(template, self.examples, self.config)
            candidates = model.learn()
            results.append(candidates)
        
        return results
    
    def learn_flat(self) -> List[ConstraintCandidate]:
        """
        Learn parameters and return flattened list of all candidates.
        
        Returns:
            Flat list of all constraint candidates across templates
        """
        nested = self.learn()
        return [candidate for template_candidates in nested 
                for candidate in template_candidates]

