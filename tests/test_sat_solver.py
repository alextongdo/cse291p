import operator
import sympy as sym
from z3 import z3  # type: ignore

from cse291p.pipeline.view.builder import ViewBuilder
from cse291p.pipeline.constraint.constraint import ConstantConstraint
from cse291p.pipeline.constraint.types import ConstraintKind
from cse291p.pipeline.integration.z3 import anchor_id_to_z3_var, constraint_to_z3_expr


def test_z3_constraint_satisfaction_constant_width():
    # build simple view with width to constrain
    root = ViewBuilder(name="root", rect=(0, 0, 100, 100)).build(number_type=sym.Rational)

    # y = b (width = 80)
    cn = ConstantConstraint(kind=ConstraintKind.SIZE_CONSTANT,
                            y_id=root.width_anchor.id,
                            b=sym.Rational(80),
                            op=operator.eq)

    s = z3.Optimize()
    conf_idx = 0
    # layout axioms: width = right - left
    w = anchor_id_to_z3_var(root.width_anchor.id, conf_idx)
    l = anchor_id_to_z3_var(root.left_anchor.id, conf_idx)
    r = anchor_id_to_z3_var(root.right_anchor.id, conf_idx)
    s.add(w == (r - l))
    # add constraint
    s.add(constraint_to_z3_expr(cn, conf_idx))
    # allow any placement:
    s.add(l >= 0); s.add(r >= 0)
    assert s.check() == z3.sat

