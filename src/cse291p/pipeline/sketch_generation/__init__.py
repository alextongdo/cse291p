"""Sketch generation (local inference) - generate constraint templates.

Reimplements:
- mockdown/src/mockdown/instantiation/__init__.py (factory & exports)
"""

import os

from .types import IConstraintInstantiator
from .numpy import NumpyConstraintInstantiator


def get_prolog_instantiator_factory():
    """Return PrologConstraintInstantiator class if available (non-Windows)."""
    if os.name != 'nt':
        from .prolog import PrologConstraintInstantiator
        return PrologConstraintInstantiator
    else:
        return lambda _: NotImplemented


__all__ = [
    'IConstraintInstantiator',
    'NumpyConstraintInstantiator',
    'get_prolog_instantiator_factory'
]


