import pytest
import os
from fslab_checker import fslab_utils_v2 as utils

# --- Tests for normalize_spaces ---

def test_normalize_spaces_basic():
    text = "hello world"
    assert utils.normalize_spaces(text) == "hello world"

def test_normalize_spaces_complex():
    text = "  foo    bar   \n  baz  "
    assert utils.normalize_spaces(text) == "foo bar baz"

def test_normalize_spaces_empty():
    assert utils.normalize_spaces("   ") == ""


# --- Tests for parse_dict_safe ---

def test_parse_dict_valid_standard_format():
    """
    Test that standard Python dictionary syntax is parsed correctly.
    """
    input_str = "{'key': 'value', 'num': 123, 'bool': True}"
    expected = {'key': 'value', 'num': 123, 'bool': True}
    assert utils.parse_dict_safe(input_str) == expected

def test_parse_dict_valid_nested():
    """
    Test nested dictionaries. Note that keys must be quoted now.
    """
    input_str = "{'outer': {'inner': 'value'}}"
    expected = {'outer': {'inner': 'value'}}
    assert utils.parse_dict_safe(input_str) == expected

def test_parse_dict_rejects_unquoted_keys():
    """
    Constraint Check: The safe parser must reject unquoted keys (e.g., {key: val}).
    This is a trade-off for security.
    """
    input_str = "{key: value, status: OK}"
    
    with pytest.raises(AssertionError) as excinfo:
        utils.parse_dict_safe(input_str)
    
    assert "Invalid string" in str(excinfo.value)

def test_parse_dict_invalid_format():
    input_str = "{invalid_dict"
    with pytest.raises(AssertionError) as excinfo:
        utils.parse_dict_safe(input_str)
    assert "Invalid string" in str(excinfo.value)


# --- Security Test for parse_dict ---

def test_parse_dict_security_no_code_execution():
    """
    Security Check: Ensure that malicious code execution is BLOCKED.
    The function should raise an error instead of running the code.
    """
    # This file serves as proof if the exploit succeeds (it should not).
    proof_file = "security_breach.txt"
    if os.path.exists(proof_file):
        os.remove(proof_file)

    # Malicious input trying to run system commands
    malicious_input = f"{{'exploit': __import__('os').system('touch {proof_file}')}}"
    
    # Expectation: parse_dict_safe raises AssertionError (wrapping the ValueError from ast)
    with pytest.raises(AssertionError):
        utils.parse_dict_safe(malicious_input)
    
    # Critical: Verify the file was NOT created
    assert not os.path.exists(proof_file), "Security failed: Malicious code was executed!"


# --- Robustness Test ---

def test_parse_dict_nesting_limit():
    """
    Robustness: Verify behavior near the parser's nesting limit.
    Note: Inputs must use quoted keys now.
    """
    # 1. Test a Safe Depth (Should Pass)
    safe_depth = 150
    # UPDATED: Added quotes to keys 'a'
    safe_str = "{" + "'a':{" * safe_depth + "1" + "}" * (safe_depth + 1)
    
    try:
        res = utils.parse_dict_safe(safe_str)
        curr = res
        for _ in range(safe_depth):
            curr = curr['a']
        # UPDATED: The deepest value is {1} (set), not 1 (int)
        assert curr == {1}
    except Exception as e:
        pytest.fail(f"Safe depth ({safe_depth}) failed: {e}")

    # 2. Test the Limit (Should fail gracefully)
    unsafe_depth = 300
    unsafe_str = "{" + "'a':{" * unsafe_depth + "1" + "}" * (unsafe_depth + 1)
    
    with pytest.raises(AssertionError) as excinfo:
        utils.parse_dict_safe(unsafe_str)
    
    assert "Invalid string" in str(excinfo.value)


# --- Tests for hex_to_int ---

def test_hex_to_int_valid():
    assert utils.hex_to_int("0x10") == 16
    assert utils.hex_to_int("FF") == 255
    assert utils.hex_to_int("0") == 0

def test_hex_to_int_invalid():
    with pytest.raises(AssertionError) as excinfo:
        utils.hex_to_int("invalid_hex")
    assert "Invalid hex string" in str(excinfo.value)


# --- Tests for is_in_same_page ---

def test_is_in_same_page_true():
    addr1 = 0x1000
    addr2 = 0x1050
    assert utils.is_in_same_page(addr1, addr2) is True

def test_is_in_same_page_false():
    addr1 = 0x1000
    addr2 = 0x2000
    assert utils.is_in_same_page(addr1, addr2) is False

def test_is_in_same_page_boundary():
    addr1 = 4095
    addr2 = 4096
    assert utils.is_in_same_page(addr1, addr2) is False
    
def test_is_in_same_page_negative():
    assert utils.is_in_same_page(-1, -1) is True 
    assert utils.is_in_same_page(-1, 0) is False


# --- Tests for check_exists ---

class MockMessageType:
    pass

def test_check_exists_valid():
    data = {'target_key': 'target_value'}
    result = utils.check_exists(data, 'target_key', MockMessageType)
    assert result == 'target_value'

def test_check_exists_missing():
    data = {'other_key': 'value'}
    with pytest.raises(AssertionError) as excinfo:
        utils.check_exists(data, 'missing_key', MockMessageType)
    
    msg = str(excinfo.value)
    assert "Invalid MockMessageType" in msg
    assert "missing_key" in msg
    
def test_check_exists_none_value():
    """
    Verify that check_exists does NOT raise an error if the key exists
    but the value is None.
    """
    class MockType: pass
    data = {'key_with_none': None}
    
    # This should pass and return None, not raise AssertionError
    result = utils.check_exists(data, 'key_with_none', MockType)
    assert result is None