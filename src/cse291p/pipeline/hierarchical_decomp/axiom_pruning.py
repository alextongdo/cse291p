"""Global axiom-based constraint pruning.

Prunes constraint candidates that violate global axioms (containment, layout axioms)
before Max-SMT solving to reduce search space.
"""

import logging
from typing import List

from cse291p.pipeline.bayes.types import ConstraintCandidate
from cse291p.pipeline.view import IView
from cse291p.pipeline.hierarchical_decomp.types import ISizeBounds
from cse291p.pipeline.integration.z3 import constraint_to_z3_expr, anchor_id_to_z3_var
from cse291p.pipeline.hierarchical_decomp.types import BasePruningMethod
from cse291p.pipeline.hierarchical_decomp.blackbox import BlackBoxPruner
from cse291p.types import NT

logger = logging.getLogger(__name__)


def prune_axiom_violators(
    candidates: List[ConstraintCandidate],
    examples: List[IView[NT]],
    bounds: ISizeBounds,
    parallel: bool = False
) -> List[ConstraintCandidate]:
    """Prune constraints that violate global axioms on any example.
    
    Global axioms include:
    - Layout axioms: width = right - left, height = bottom - top, etc.
    - Containment axioms: child within parent bounds
    - Non-negativity: all anchors >= 0
    
    Args:
        candidates: List of constraint candidates from Bayesian learning
        examples: List of example view hierarchies
        bounds: Size bounds for the examples
        parallel: Whether to parallelize checks (future enhancement)
    
    Returns:
        Filtered list of candidates that satisfy global axioms
    """
    import z3
    
    # Create a dummy pruner instance to use its methods
    # We'll use BlackBoxPruner which extends BasePruningMethod
    dummy_pruner = BlackBoxPruner(examples[:1], bounds, solve_unambig=False)
    
    valid_candidates = []
    violations_by_type = {'containment': 0, 'layout': 0, 'other': 0}
    
    for cand in candidates:
        # Check if constraint violates axioms on any example
        violates = False
        violation_type = None
        
        for example in examples:
            solver = z3.Solver()
            
            # Add layout axioms (width = right - left, etc.)
            dummy_pruner.add_layout_axioms(solver, 0, [example], x_dim=True)
            dummy_pruner.add_layout_axioms(solver, 0, [example], x_dim=False)
            
            # Add containment axioms (child within parent)
            dummy_pruner.add_containment_axioms(solver, 0, example, x_dim=True)
            dummy_pruner.add_containment_axioms(solver, 0, example, x_dim=False)
            
            # Add this constraint
            solver.add(constraint_to_z3_expr(cand.constraint, 0))
            
            # Fix example anchor values
            for view in example:
                for anchor in view.anchors:
                    var = anchor_id_to_z3_var(anchor.id, 0)
                    solver.add(var == float(anchor.value))
            
            # Check satisfiability
            result = solver.check()
            if result == z3.unsat:
                violates = True
                # Determine violation type for debugging
                violation_type = _classify_violation(cand.constraint, example, dummy_pruner)
                break
        
        if violates:
            violations_by_type[violation_type] += 1
        else:
            valid_candidates.append(cand)
    
    # Log statistics
    total_pruned = len(candidates) - len(valid_candidates)
    if total_pruned > 0:
        logger.info(f"Pruned {total_pruned} axiom-violating constraints:")
        logger.info(f"  Containment violations: {violations_by_type['containment']}")
        logger.info(f"  Layout axiom violations: {violations_by_type['layout']}")
        logger.info(f"  Other violations: {violations_by_type['other']}")
    
    return valid_candidates


def _classify_violation(constraint, example: IView[NT], pruner: BasePruningMethod) -> str:
    """Classify the type of axiom violation for debugging."""
    import z3
    
    # Check containment separately
    solver_containment = z3.Solver()
    pruner.add_containment_axioms(solver_containment, 0, example, x_dim=True)
    pruner.add_containment_axioms(solver_containment, 0, example, x_dim=False)
    solver_containment.add(constraint_to_z3_expr(constraint, 0))
    
    # Fix example values
    for view in example:
        for anchor in view.anchors:
            var = anchor_id_to_z3_var(anchor.id, 0)
            solver_containment.add(var == float(anchor.value))
    
    if solver_containment.check() == z3.unsat:
        return 'containment'
    
    # Check layout axioms separately
    solver_layout = z3.Solver()
    pruner.add_layout_axioms(solver_layout, 0, [example], x_dim=True)
    pruner.add_layout_axioms(solver_layout, 0, [example], x_dim=False)
    solver_layout.add(constraint_to_z3_expr(constraint, 0))
    
    for view in example:
        for anchor in view.anchors:
            var = anchor_id_to_z3_var(anchor.id, 0)
            solver_layout.add(var == float(anchor.value))
    
    if solver_layout.check() == z3.unsat:
        return 'layout'
    
    return 'other'

