"""Load view hierarchies from dictionaries.

Reimplements:
- mockdown/model/view/loader.py (lines 1-51)
"""

import json
from typing import Any, Dict, Protocol, TextIO, Type, Literal

import numpy as np

from .types import IView
from .builder import ViewBuilder
from cse291p.types import NT, unreachable


class IViewLoader(Protocol[NT]):
    """View loader protocol.
    
    Reimplements: mockdown/model/view/loader.py lines 11-14
    """
    def load_dict(self, d: Dict[str, Any]) -> IView[NT]: ...

    def load_file(self, src: TextIO) -> IView[NT]: ...


class ViewLoader(IViewLoader[NT]):
    """Concrete view loader.
    
    Reimplements: mockdown/model/view/loader.py lines 17-50
    """
    def __init__(self: IViewLoader[NT],
                 number_type: Type[NT],
                 input_format: Literal['default', 'bench'] = 'default',
                 debug_noise: float = 0):
        """Reimplements: mockdown/model/view/loader.py lines 18-24"""
        self.number_type = number_type
        self.input_format = input_format
        self.debug_noise = debug_noise

    def load_file(self, src: TextIO) -> IView[NT]:
        """Reimplements: mockdown/model/view/loader.py lines 26-28"""
        d = json.load(src)
        return self.load_dict(d)

    def load_dict(self, data: Dict[str, Any]) -> IView[NT]:
        """Reimplements: mockdown/model/view/loader.py lines 30-50"""
        def recurse(d: Dict[str, Any]) -> ViewBuilder:
            if self.input_format == 'default':
                name, rect = d['name'], d['rect']
            elif self.input_format == 'bench':
                name = d['name']
                rect = (d['left'], d['top'], d['left'] + d['width'], d['top'] + d['height'])
            else:
                unreachable(self.input_format)

            if self.debug_noise:
                rect = tuple(rect + self.debug_noise * np.random.rand(4))

            if 'children' not in d or len(d['children']) == 0:
                return ViewBuilder(name=name, rect=rect)
            else:
                child_builders = [recurse(child_dict) for child_dict in d['children']]
                return ViewBuilder(name=name, rect=rect, children=child_builders)

        builder = recurse(data)
        return builder.build(number_type=self.number_type)
