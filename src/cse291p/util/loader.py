"""Utility functions for loading scraped data into the pipeline."""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path for imports
_loader_file = Path(__file__).resolve()
# Go from: src/cse291p/util/loader.py -> project root
_project_root = _loader_file.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.types import View


def load_scraped_examples(file_path: str | Path) -> List[View]:
    """Load examples from a scraped JSON file and convert them to View objects.
    
    The scraped JSON format has:
    {
        "meta": {...},
        "examples": [
            {
                "name": "...",
                "rect": [left, top, right, bottom],
                "children": [...]
            },
            ...
        ]
    }
    
    Args:
        file_path: Path to the scraped JSON file
        
    Returns:
        List of View objects ready for use with the pipeline
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Scraped file not found: {file_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'examples' not in data:
        raise ValueError(f"Invalid scraped format: missing 'examples' key in {file_path}")
    
    examples = data['examples']
    views = []
    
    for example_dict in examples:
        view = _dict_to_view(example_dict)
        views.append(view)
    
    return views


def _dict_to_view(d: Dict[str, Any]) -> View:
    """Recursively convert a dictionary to a View object.
    
    Converts rect from list to tuple and recursively processes children.
    """
    # Convert rect list to tuple (Pydantic will handle this, but being explicit)
    view_dict = d.copy()
    if 'rect' in view_dict and isinstance(view_dict['rect'], list):
        view_dict['rect'] = tuple(view_dict['rect'])
    
    # Recursively convert children
    if 'children' in view_dict and view_dict['children']:
        view_dict['children'] = [_dict_to_view(child) for child in view_dict['children']]
    
    return View(**view_dict)


def load_examples_from_json(file_path: str | Path) -> List[View]:
    """Load examples from a JSON file (supports both scraped format and direct examples list).
    
    This function is more flexible and can handle:
    1. Scraped format: {"meta": {...}, "examples": [...]}
    2. Direct format: [{"name": "...", "rect": [...], "children": [...]}, ...]
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of View objects ready for use with the pipeline
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check if it's scraped format (has 'examples' key) or direct format (list)
    if isinstance(data, dict) and 'examples' in data:
        examples = data['examples']
    elif isinstance(data, list):
        examples = data
    else:
        raise ValueError(
            f"Invalid format: expected either {{'examples': [...]}} or [...] list, "
            f"got {type(data).__name__}"
        )
    
    views = []
    for example_dict in examples:
        view = _dict_to_view(example_dict)
        views.append(view)
    
    return views

