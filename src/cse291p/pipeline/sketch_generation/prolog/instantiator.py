"""Prolog-based sketch generation instantiator.

Reimplements:
- mockdown/src/mockdown/instantiation/prolog/instantiator.py (lines 1-51)
"""

from typing import Sequence, Set

from cse291p.pipeline.constraint import IConstraint
from cse291p.pipeline.sketch_generation.types import IConstraintInstantiator
from cse291p.pipeline.sketch_generation.prolog.logic import valid_constraints
from cse291p.pipeline.sketch_generation.visibility import visible_pairs

from cse291p.pipeline.view import IView
from cse291p.types import NT


class PrologConstraintInstantiator(IConstraintInstantiator[NT]):
    def __init__(self, examples: Sequence[IView[NT]]):
        super().__init__(examples)
        self.examples = examples

    def detect_visibilities(self):
        examples = self.examples

        edge_pair_sets = [
            visible_pairs(example, deep=True)
            for example
            in examples
        ]

        anchor_pair_sets = [
            [(e1.anchor, e2.anchor) for (e1, e2) in edge_pair_set]
            for edge_pair_set
            in edge_pair_sets
        ]

        return anchor_pair_sets

    def instantiate(self) -> Sequence[IConstraint]:
        examples = self.examples
        anchor_pair_sets = self.detect_visibilities()

        constraint_sets = {
            valid_constraints(examples[i], anchor_pair_sets[i])
            for i
            in range(len(examples))
        }

        all_constraints: Set[IConstraint] = set()
        for constraint_set in constraint_sets:
            all_constraints = all_constraints.union(constraint_set)

        return list(all_constraints)


