"""Sketch generation interfaces.

Reimplements:
- mockdown/src/mockdown/instantiation/types.py (lines 1-24)
"""

from abc import abstractmethod
from typing import Protocol, Sequence

from cse291p.pipeline.constraint import IConstraint
from cse291p.pipeline.view import IView
from cse291p.types import NT


class IConstraintInstantiator(Protocol[NT]):
    """An instantiation engine that generates constraint templates.

    Reimplements: mockdown/instantiation/types.py
    """

    @abstractmethod
    def __init__(self, examples: Sequence[IView[NT]]):
        ...

    @abstractmethod
    def instantiate(self) -> Sequence[IConstraint]:
        """Given examples, instantiate a set of constraint templates to train."""
        ...


