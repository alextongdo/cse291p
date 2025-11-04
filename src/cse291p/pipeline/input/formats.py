"""Input format adapters (default vs bench formats).

Reimplements:
- mockdown/model/view/loader.py lines 32-38 (format detection and rect conversion)
"""

from typing import Dict, Any, List
from .schema import ViewDict


def normalize_to_default_format(data: Dict[str, Any], format_type: str) -> List[ViewDict]:
    """Convert input data to normalized default format.
    
    Reimplements: mockdown/run.py lines 93-96 (format-based data extraction)
    """
    if format_type == 'default':
        examples_data = data["examples"]
    elif format_type == 'bench':
        examples_data = data["train"]
    else:
        raise ValueError(f"Unknown format: {format_type}")
    
    normalized = []
    for example in examples_data:
        normalized.append(_normalize_view_dict(example, format_type))
    
    return normalized


def _normalize_view_dict(view_data: Dict[str, Any], format_type: str) -> ViewDict:
    """Normalize a single view dict to default format.
    
    Reimplements: mockdown/model/view/loader.py lines 32-38:
    - Lines 32-33: if self.input_format == 'default': name, rect = d['name'], d['rect']
    - Lines 34-36: elif self.input_format == 'bench': rect = (d['left'], d['top'], d['left'] + d['width'], d['top'] + d['height'])
    """
    if format_type == 'default':
        # Already in correct format (mockdown lines 32-33)
        return ViewDict(**view_data)
    elif format_type == 'bench':
        # Convert left/top/width/height to rect (mockdown lines 34-36)
        name = view_data['name']
        left = view_data['left']
        top = view_data['top']
        width = view_data['width']
        height = view_data['height']
        rect = [left, top, left + width, top + height]  # Exact conversion from mockdown
        
        children = []
        if 'children' in view_data:
            children = [_normalize_view_dict(child, format_type) for child in view_data['children']]
        
        return ViewDict(name=name, rect=rect, children=children)
    else:
        raise ValueError(f"Unknown format: {format_type}")
