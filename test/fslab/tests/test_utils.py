import pytest
import os
from fslab_checker import fslab_utils as utils


# --- Tests for normalize_spaces ---

def test_normalize_spaces_basic():
    text = "hello world"
    assert utils.normalize_spaces(text) == "hello world"

def test_normalize_spaces_complex():
    text = "  foo    bar   \n  baz  "
    assert utils.normalize_spaces(text) == "foo bar baz"

def test_normalize_spaces_empty():
    assert utils.normalize_spaces("   ") == ""


# --- Tests for parse_dict ---

def test_parse_dict_quoted_keys():
    input_str = "{'key': 'value', 'num': 123}"
    expected = {'key': 'value', 'num': 123}
    assert utils.parse_dict(input_str) == expected

def test_parse_dict_unquoted_keys():
    # This tests the NameError handling logic in the utility
    input_str = "{key: value, status: OK}"
    expected = {'key': 'value', 'status': 'OK'}
    assert utils.parse_dict(input_str) == expected

def test_parse_dict_nested():
    input_str = "{outer: {inner: value}}"
    expected = {'outer': {'inner': 'value'}}
    assert utils.parse_dict(input_str) == expected

def test_parse_dict_invalid_format():
    input_str = "{invalid_dict"
    with pytest.raises(AssertionError) as excinfo:
        utils.parse_dict(input_str)
    assert "Invalid string" in str(excinfo.value)

# --- Security Test for parse_dict ---

def test_parse_dict_vulnerability_rce():
    """
    Demonstrates the security vulnerability (Remote Code Execution) in parse_dict.
    Goal: Execute malicious Python code via eval() to create a file on the system.
    """
    # Define a filename to prove the exploit was successful
    proof_file = "you_have_been_hacked.txt"
    
    # Ensure the file does not exist before the test starts
    if os.path.exists(proof_file):
        os.remove(proof_file)

    # --- Malicious Payload ---
    # This string looks like a dictionary structure.
    # However, its value contains Python code: importing 'os' and executing 'touch' to create a file.
    # eval() will execute this code.
    malicious_input = f"{{'exploit_result': __import__('os').system('touch {proof_file}')}}"
    
    # Execute the vulnerable function
    # os.system usually returns 0 (success), so the resulting dict will be {'exploit_result': 0}
    utils.parse_dict(malicious_input)
    
    # --- Verify the result ---
    # Check if proof_file was created. If it exists, the malicious code ran.
    exploit_successful = os.path.exists(proof_file)
    
    # Cleanup: remove the proof file
    if exploit_successful:
        os.remove(proof_file)

    # If exploit_successful is True, the vulnerability is confirmed.
    assert exploit_successful, "Vulnerability test failed: The malicious code was not executed."

def test_parse_dict_nesting_limit():
    """
    Robustness: Verify behavior near the parser's nesting limit.
    
    Findings:
    - Depth ~199: Safe (Passes).
    - Depth ~200+: Fails (Caught by catch-all exception in parse_dict).
    
    Explanation:
    Python's 'eval()' requires compiling the string first. The CPython parser 
    has a stricter stack depth limit for nested syntax (around 200) than 
    the runtime recursion limit (usually 1000).
    """
    
    # 1. Test a Safe Depth (Should Pass)
    # We use 150 to be safe across different OS/Environments.
    safe_depth = 150
    safe_str = "{" + "'a':{" * safe_depth + "1" + "}" * (safe_depth + 1)
    
    try:
        res = utils.parse_dict(safe_str)
        # Verify we can traverse to the bottom
        curr = res
        for _ in range(safe_depth):
            curr = curr['a']
        assert curr == {1}
    except Exception as e:
        pytest.fail(f"Safe depth ({safe_depth}) failed surprisingly: {e}")

    # 2. Test the Limit (Should fail gracefully, not crash the interpreter)
    # We expect parse_dict to raise AssertionError when the limit is hit.
    unsafe_depth = 300
    unsafe_str = "{" + "'a':{" * unsafe_depth + "1" + "}" * (unsafe_depth + 1)
    
    with pytest.raises(AssertionError) as excinfo:
        utils.parse_dict(unsafe_str)
    
    # Verify the error message confirms it was caught by our logic
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
    # 4KB page size = 4096 bytes (0x1000)
    addr1 = 0x1000
    addr2 = 0x1050
    assert utils.is_in_same_page(addr1, addr2) is True

def test_is_in_same_page_false():
    addr1 = 0x1000  # Page 1
    addr2 = 0x2000  # Page 2
    assert utils.is_in_same_page(addr1, addr2) is False

def test_is_in_same_page_boundary():
    addr1 = 4095  # 0xFFF (Page 0)
    addr2 = 4096  # 0x1000 (Page 1)
    assert utils.is_in_same_page(addr1, addr2) is False
    
def test_is_in_same_page_negative():
    """Boundary: Check behavior with negative addresses or edge cases."""
    # Insure negative numbers won't cause unexpected True
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
    
    # Verify error message contains the class name and the missing key
    msg = str(excinfo.value)
    assert "Invalid MockMessageType" in msg
    assert "missing_key" in msg
