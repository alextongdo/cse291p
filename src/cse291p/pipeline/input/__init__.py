"""Stage 1: JSON Input - Load and validate input examples."""

from .schema import ViewDict, DefaultFormatInput, BenchFormatInput
from .formats import normalize_to_default_format
from .loader import load_from_file, load_from_dict

__all__ = [
    'ViewDict', 'DefaultFormatInput', 'BenchFormatInput',
    'normalize_to_default_format',
    'load_from_file', 'load_from_dict',
]
