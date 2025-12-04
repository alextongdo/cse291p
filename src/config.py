from pydantic import BaseModel, Field


class LearningConfig(BaseModel):
    """Configuration for Bayesian parameter learning."""

    std_threshold: float = Field(
        3.0,
        description="Maximum allowed standard deviation for anchor positions before"
        " template rejection.",
    )
    max_offset: int = Field(
        1000, description="Maximum possible value learned for |b| in y = a * x + b."
    )
    max_denominator: int = Field(
        100,
        description="Maximum denominator value of fractions learned for a in"
        " y = a * x + b.",
    )
    expected_sb_depth: int = Field(
        5,
        description="Defines Stern-Brocot depth prior for fractions. Decrease to"
        " heavily bias towards simple fractions.",
    )
    a_alpha: float = Field(
        0.05,
        description="Probability of failing to capture true value of a in"
        " y = a * x + b. Increasing will allow for additional exploration.",
    )
    b_alpha: float = Field(
        0.05,
        description="Probability of failing to capture true value of b in"
        " y = a * x + b. Increasing will allow for additional exploration.",
    )


class ConditionalLearningConfig(LearningConfig):
    a_cluster_threshold: float = Field(
        0.1,
        description="Relative threshold for clustering 'a' values (ratios). "
        "E.g., 0.1 means 10% relative difference allowed within a cluster.",
    )
    b_cluster_threshold: float = Field(
        3.0,
        description="Absolute threshold for clustering 'b' values (offsets). "
        "E.g., 5 means |b1-b2| ≤ 5 allowed within a cluster.",
    )
