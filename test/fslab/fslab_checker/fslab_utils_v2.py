import re
from typing import Any, Dict

# Inhance parse_dict() security
import ast

def normalize_spaces(text: str) -> str:
    """
    Normalize multiple spaces to a single space and strip leading/trailing whitespace.
    Optimization: split() + join() is faster than re.sub() for this specific task.
    """
    if not text:
        return ""
    return " ".join(text.split())

    
def parse_dict_safe(s: str) -> Dict[str, Any]:
    """
    Safely parse a string into a dictionary using ast.literal_eval.
    
    This ignores the unsafe eval-based implementation and uses Python's
    built-in mechanism for safely evaluating literals.
    """
    try:
        # ast.literal_eval can only parse Python's basic data structures.
        # It will not execute functions or commands, making it safe.
        d = ast.literal_eval(s)
    except (ValueError, SyntaxError, RecursionError) as e:
        # Security/Performance: Truncate the input string in the error message
        # to prevent log flooding if the input is massive.
        snippet = s[:50] + "..." if len(s) > 50 else s
        raise AssertionError(f"Invalid string format: {snippet}. Error: {e}")
    
    if not isinstance(d, dict):
        # Also truncate here
        snippet = s[:50] + "..." if len(s) > 50 else s
        raise AssertionError(f"Parsed result is not a dictionary: {snippet}")
        
    return d

def hex_to_int(value: str, max_len: int = 64) -> int:
    """
    Convert a hexadecimal string to an integer.
    Includes basic protection against extremely long strings (DoS).
    """
    # Optional protection: Limit input length.
    # e.g., if checking 64-bit addresses, length shouldn't exceed 18 chars.
    # (0x + up to 16 hex digits)
    if len(value) > max_len:
        raise AssertionError(f"Hex string too long: {len(value)} characters")
    
    try:
        return int(value, base=16)
    except ValueError:
        raise AssertionError(f"Invalid hex string: {value}")

def is_in_same_page(a: int, b: int) -> bool:
    """Check if two addresses are in the same 4KB page."""
    return (a & ~4095) == (b & ~4095)

def check_exists(dc: dict, key: str, msg_type) -> Any:
    """
    Check if a key exists in a dictionary, raise error if not.
    Fixes the bug where value is None.
    """
    if key not in dc:
        raise AssertionError(f"Invalid {msg_type.__name__}: key '{key}' not in {dc}")
    return dc[key]