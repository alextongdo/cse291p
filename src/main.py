from src.instantiation import ConditionalTemplateInstantiator, TemplateInstantiator
from src.learning import BayesianLearning, ConditionalBayesianLearning
from src.pruning import ConditionalHierarchicalPruner, HierarchicalPruner
from src.types import View


class Mockdown:

    def fit(self, examples: list[View]) -> None:
        templates = TemplateInstantiator(examples).instantiate()
        candidates = BayesianLearning(examples=examples, seed=42).learn(templates)
        selected = HierarchicalPruner(examples).prune(candidates)
        self.constraints = selected

    def predict(self, width: int, height: int):
        # Should use kiwi solver to solver for a layout for the unseen width + height
        pass


class ConditionalMockdown:

    def fit(self, examples: list[View]) -> None:
        example_idxs_to_templates_map = ConditionalTemplateInstantiator(
            examples=examples
        ).instantiate()
        example_idxs_to_constrs_map = ConditionalBayesianLearning(
            examples=examples, seed=42
        ).learn(example_idxs_to_templates_map)
        ex_to_selected_map = ConditionalHierarchicalPruner(examples=examples).prune(
            example_idxs_to_constrs_map
        )
        self.examples = examples
        self.ex_to_constrs_map = ex_to_selected_map

    def predict(self, width: int, height: int):
        # Should use kiwi solver to solver for a layout for the unseen width + height
        pass
