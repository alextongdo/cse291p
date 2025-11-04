"""Load JSON input examples from files or dictionaries.

Reimplements:
- mockdown/model/view/loader.py IViewLoader.load_file() and load_dict()
- mockdown/cli.py line 112 (json.load(input))
"""

import json
from typing import Dict, Any, List, Literal, TextIO
from .schema import ViewDict, DefaultFormatInput, BenchFormatInput
from .formats import normalize_to_default_format


def load_from_file(path: str, format_type: Literal['default', 'bench'] = 'default') -> List[ViewDict]:
    """Load examples from a JSON file.
    
    Reimplements: mockdown/model/view/loader.py lines 26-28:
    - def load_file(self, src: TextIO) -> IView[NT]:
    -     d = json.load(src)
    -     return self.load_dict(d)
    """
    with open(path, 'r') as f:
        data = json.load(f)
    return load_from_dict(data, format_type)


def load_from_dict(data: Dict[str, Any], format_type: Literal['default', 'bench'] = 'default') -> List[ViewDict]:
    """Load examples from a dictionary.
    
    Reimplements: mockdown/model/view/loader.py ViewLoader.load_dict() method
    """
    # Validate the input structure (adds validation that mockdown didn't have)
    if format_type == 'default':
        validated = DefaultFormatInput(**data)
        return validated.examples
    elif format_type == 'bench':
        validated = BenchFormatInput(**data)
        # Convert bench format to default format
        return normalize_to_default_format({'train': validated.train}, 'bench')
    else:
        raise ValueError(f"Unknown format: {format_type}")
