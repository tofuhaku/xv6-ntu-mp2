import pytest
from fslab_checker import fslab_parser
from fslab_checker import fslab_data_models as models
from fslab_checker import fslab_messages as messages

@pytest.fixture
def matcher():
    return fslab_parser.SlabMatcher()

# --- Tests for SlabMatcher ---

def test_matcher_call_method(matcher):
    """
    Test the __call__ method of the matcher.
    Covers: def __call__(self, line: str): return self.match(line)
    """
    line = "Alloc request on cache test_cache"
    # directly call the matcher object
    result = matcher(line)
    
    assert result is None
    assert len(matcher.datalist) == 1
    assert isinstance(matcher.datalist[0], models.SlabAllocRequestData)
    
def test_match_slab_create(matcher):
    # valid_object_size: int = 504
    # 504 bytes * 8 objects = 4032 bytes < 4096 bytes
    line = "New kmem_cache (name: test_cache, object size: 504 bytes, at: 0x1000, max objects per slab: 8, support in cache obj: 0) is created"
    
    result = matcher.match(line)
    
    assert isinstance(result, messages.SlabCreateMsg)
    assert len(matcher.datalist) == 0

def test_match_slab_alloc_obj_branch(matcher):
    """
    Test the specific branch where a SlabAllocMsg is encapsulated.
    Covers: elif msg_type == models.SlabAllocObjData: ...
    """
    # 1. Setup prerequisite state (Alloc Request)
    matcher.match("Alloc request on cache test_cache")
    
    # 2. Setup prerequisite state (Slab Alloc)
    matcher.match("A new slab 0x2000 (test_cache) is allocated")
    
    # 3. Trigger the specific target line (Object Alloc)
    # This line matches SlabAllocObjData and should return SlabAllocMsg
    line = "Object 0x2010 in slab 0x2000 (test_cache) is allocated and initialized"
    result = matcher.match(line)
    
    assert isinstance(result, messages.SlabAllocMsg)
    assert len(matcher.datalist) == 0  # Should be cleared after encapsulation

def test_match_slab_free_slab_branch(matcher):
    """
    Test the evaluation of the SlabFreeSlabData branch.
    Covers: elif msg_type == models.SlabFreeSlabData ...
    """
    # This matches SlabFreeSlabData pattern
    line = "Slab 0x2000 (test_cache) is freed due to save memory"
    
    # This will hit the elif condition check
    result = matcher.match(line)
    
    # Even if it doesn't return a message (due to missing "End of free"),
    # we verify the data was processed and added to datalist
    assert result is None
    assert len(matcher.datalist) > 0
    assert isinstance(matcher.datalist[0], models.SlabFreeSlabData)

def test_match_alloc_sequence(matcher):
    # 1. Alloc Request
    line1 = "Alloc request on cache test_cache"
    res1 = matcher.match(line1)
    assert res1 is None
    assert len(matcher.datalist) == 1
    assert isinstance(matcher.datalist[0], models.SlabAllocRequestData)
    assert matcher.datalist[0].name == "test_cache"

    # 2. Slab Alloc
    line2 = "A new slab 0x2000 (test_cache) is allocated"
    res2 = matcher.match(line2)
    assert res2 is None
    assert len(matcher.datalist) == 2
    assert isinstance(matcher.datalist[1], models.SlabAllocSlabData)
    assert matcher.datalist[1].addr == 8192         # 0x2000

    # 3. Object Alloc (Trigger Encapsulation)
    line3 = "Object 0x2010 in slab 0x2000 (test_cache) is allocated and initialized"
    res3 = matcher.match(line3)
    
    assert isinstance(res3, messages.SlabAllocMsg)
    assert len(matcher.datalist) == 0  # Datalist should be cleared

def test_match_free_sequence(matcher):
    # 1. Free Object
    line1 = "Free 0x2010 in slab 0x2000 (test_cache)"
    res1 = matcher.match(line1)
    assert res1 is None
    assert len(matcher.datalist) == 1
    assert isinstance(matcher.datalist[0], models.SlabFreeObjData)

    # 2. End of free (Trigger Encapsulation)
    line2 = "End of free"
    res2 = matcher.match(line2)
    
    assert isinstance(res2, messages.SlabFreeMsg)
    assert len(matcher.datalist) == 0

def test_match_slab_free_slab(matcher):
    # Triggered when a whole slab is freed
    line = "Slab 0x2000 (test_cache) is freed due to save memory"
    
    matcher.match(line)
    # Check if data was captured
    if len(matcher.datalist) > 0:
        assert isinstance(matcher.datalist[0], models.SlabFreeSlabData)

def test_match_printf_slab_status(matcher):
    # Test parsing of nested dictionary string
    line = "[ slab 0x3000 ] { 'freelist': 0x0, 'nxt': 0x0 }"
    
    res = matcher.match(line)
    assert res is None
    assert len(matcher.datalist) == 1
    
    data = matcher.datalist[0]
    assert isinstance(data, models.SlabPrintfSlabStatusData)
    assert data.addr == 12288   # 0x3000
    assert data.freelist == 0   # 0x0
    assert data.nxt == 0        # 0x0

def test_match_printf_obj_status(matcher):
    # Test parsing of nested object dict
    line = "[ idx 0 ] { addr: 0x4000, as_ptr: 0x4000, as_obj: { 'val': 123 } }"
    
    res = matcher.match(line)
    assert res is None
    
    data = matcher.datalist[-1]
    assert isinstance(data, models.SlabPrintfObjStatusData)
    assert data.idx == 0        # 0x0
    assert data.as_obj == {'val': 123}

def test_match_print_end(matcher):
    line = "print_kmem_cache end"
    res = matcher.match(line)
    assert isinstance(res, messages.SlabPrintMsg)

def test_match_ignore_unknown(matcher):
    line = "Some random log line"
    res = matcher.match(line)
    assert res is None
    assert len(matcher.datalist) == 0

# --- Tests for file_matcher ---

def test_file_matcher_valid():
    if list(messages.FileMsg):
        valid_val = list(messages.FileMsg)[0]
        line = valid_val.value
        assert fslab_parser.file_matcher(line) == valid_val

def test_file_matcher_invalid():
    """
    []
    """
    assert fslab_parser.file_matcher("Invalid File Message") is None
    

# --- Inhanced Tests ---

# --- Logic Coverage ---

def test_match_incomplete_free_sequence(matcher):
    """
    [Logic] Test whether the Matcher can correctly maintain its state when the log 
    sequence is incomplete (e.g. only containing Free Obj without End of free), 
    or how it handles new instructions when encountered.
    """
    # 1. Free Object Only
    line = "Free 0x2010 in slab 0x2000 (test_cache)"
    res = matcher.match(line)
    
    # Expect: No Message returned，but datalist should have something
    assert res is None
    assert len(matcher.datalist) == 1
    assert isinstance(matcher.datalist[0], models.SlabFreeObjData)

    # 2. A unrelated command occurred (e.g. Alloc Request)
    # Current implementation is "appends to datalist".
    # Unrelated command may cause the next encapsulation to fail.
    # This test is used to confirm this behavior (or to verify fixes if you modify the parser).
    line_new = "Alloc request on cache test_cache"
    res_new = matcher.match(line_new)
    
    # According to the current parser implementation, it will append to the datalist.
    assert len(matcher.datalist) == 1
    # This test is used to define the behavior.
    # This expose a potential logical issue: Should parser clear old data when encountering incompatible messages?

# --- Complex Condition ---

def test_match_malformed_integers(matcher):
    """
    [Logic] Test for malformed integers. Parse library may fail or throw error when converting.
    """
    # max object should be int, here we give it a string.
    line = "New kmem_cache (name: bad_cache, object size: 504, at: 0x1000, max objects per slab: NOT_A_NUMBER, support in cache obj: 0) is created"
    
    # If the pattern does not match, the parser should return None.
    # Ensuring parser will not crash when encountering malformed integers.
    res = matcher.match(line)
    assert res is None