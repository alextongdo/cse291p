"""JSON schema validation for input examples.

Reimplements:
- mockdown/run.py MockdownInput, MockdownOptions TypedDicts
- Input validation that was implicit in mockdown
"""

from typing import List, Dict, Any, Literal, Optional
from pydantic import BaseModel, Field


class ViewDict(BaseModel):
    """A view in the input JSON.
    
    Reimplements the dict structure expected by:
    - mockdown/model/view/loader.py ViewLoader.load_dict()
    """
    name: str
    rect: Optional[List[float]] = Field(None, min_length=4, max_length=4)  # [left, top, right, bottom]
    children: List['ViewDict'] = Field(default_factory=list)
    
    # For bench format (mockdown/model/view/loader.py lines 34-36)
    left: Optional[float] = None
    top: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None


class DefaultFormatInput(BaseModel):
    """Default format: examples array.
    
    Reimplements: mockdown/run.py lines 94-95 (examples_data = input_data["examples"])
    """
    examples: List[ViewDict]


class BenchFormatInput(BaseModel):
    """Bench format: train array.
    
    Reimplements: mockdown/run.py lines 96 (examples_data = input_data["train"])
    """
    train: List[ViewDict]


# Allow recursive references
ViewDict.model_rebuild()
