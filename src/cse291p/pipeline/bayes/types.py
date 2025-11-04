"""Bayesian learning interfaces and candidate type.

Reimplements:
- mockdown/src/mockdown/learning/types.py (lines 1-26)
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Protocol, List, Optional, Any

import sympy

from cse291p.pipeline.constraint import IConstraint
from cse291p.pipeline.view import IView


@dataclass(order=True)
class ConstraintCandidate:
    constraint: IConstraint
    score: float


class IConstraintLearning(Protocol):
    @abstractmethod
    def __init__(self,
                 templates: List[IConstraint],
                 samples: List[IView[sympy.Number]],
                 config: Optional[Any] = None) -> None: ...

    @abstractmethod
    def learn(self) -> List[List[ConstraintCandidate]]: ...

"""Bayesian learning types and interfaces."""

# Placeholder for learning types

