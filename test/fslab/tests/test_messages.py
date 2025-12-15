import pytest
from fslab_checker.fslab_messages import (
    SlabCreateMsg,
    SlabAllocMsg,
    SlabFreeMsg,
    SlabPrintMsg,
    ListCheckMsg
)
from fslab_checker.fslab_data_models import (
    SlabCreateData,
    SlabAllocRequestData,
    SlabAllocSlabData,
    SlabAllocObjData,
    SlabFreeObjData,
    SlabFreeSlabData,
    SlabPrintfKmemStatusData
)

# --- Fixtures ---

@pytest.fixture
def common_data():
    """Provides common data for tests."""
    valid_size = 504
    page_addr = 0x10000
    obj_addr = 0x10020
    diff_page_addr = 0x20000
    
    # Use Keyword Arguments to prevent positional mismatches
    valid_create_data = SlabCreateData(
        origin="raw",
        name="test_cache",
        object_size=valid_size,
        max_objs=10,
        in_cache_obj=0,
        addr=page_addr
    )
    
    return {
        "valid_size": valid_size,
        "page_addr": page_addr,
        "obj_addr": obj_addr,
        "diff_page_addr": diff_page_addr,
        "valid_create_data": valid_create_data
    }

def test_base_msg_repr(common_data):
    # Use class that does not override __repr__
    msg = SlabCreateMsg(common_data["valid_create_data"])
    
    result = repr(msg)
    
    # f"{self.__class__.__name__} {self.msg_data}"
    assert "SlabCreateMsg" in result
    assert "test_cache" in result

# --- Test SlabCreateMsg ---

def test_create_msg_valid(common_data):
    msg = SlabCreateMsg(common_data["valid_create_data"])
    assert msg.name == "test_cache"

def test_create_msg_invalid_arg_count(common_data):
    """Line 31: Test len(msg_data) != 1"""
    # Case 1: 0 arguments
    with pytest.raises(AssertionError, match="Expected single SlabCreateData"):
        SlabCreateMsg()
    
    # Case 2: 2 arguments
    with pytest.raises(AssertionError, match="Expected single SlabCreateData"):
        SlabCreateMsg(common_data["valid_create_data"], common_data["valid_create_data"])

def test_create_msg_invalid_type():
    """Line 31: Test not isinstance(..., SlabCreateData)"""
    with pytest.raises(AssertionError, match="Expected single SlabCreateData"):
        SlabCreateMsg("This is a string, not SlabCreateData")

def test_create_msg_content_checks(common_data):
    """Covering checks inside check() for empty name or invalid size"""
    # Empty name
    invalid_data = SlabCreateData(
        origin="raw",
        addr=common_data["page_addr"],
        name="",
        object_size=common_data["valid_size"],
        max_objs=10,
        in_cache_obj=0
    )
    with pytest.raises(AssertionError, match="Name cannot be empty"):
        SlabCreateMsg(invalid_data)
    
    # Invalid size
    invalid_data_size = SlabCreateData(
        origin="raw",
        addr=common_data["page_addr"],
        name="test",
        object_size=9999,
        max_objs=10,
        in_cache_obj=0
    )
    with pytest.raises(AssertionError, match="Invalid object_size"):
        SlabCreateMsg(invalid_data_size)

# --- Test SlabAllocMsg ---

def test_alloc_msg_arg_count():
    """Line 46: Test not (2 <= len <= 3)"""
    req = SlabAllocRequestData(origin="req", name="cache")
    # Too few args (1)
    with pytest.raises(AssertionError, match="Expected 2-3 data items"):
        SlabAllocMsg(req)
    
    # Too many args (4)
    with pytest.raises(AssertionError, match="Expected 2-3 data items"):
        SlabAllocMsg(req, req, req, req)

def test_alloc_msg_types(common_data):
    """Line 49: Test invalid types for first or last item"""
    req = SlabAllocRequestData(origin="req", name="cache")
    obj = SlabAllocObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="cache",
        slab_addr=common_data["page_addr"]
    )
    
    # First arg wrong type
    with pytest.raises(AssertionError, match="Invalid data types"):
        SlabAllocMsg("Not a RequestData", obj)
        
    # Last arg wrong type
    with pytest.raises(AssertionError, match="Invalid data types"):
        SlabAllocMsg(req, "Not an AllocObjData")

def test_alloc_msg_name_checks(common_data):
    """Line 59: Name consistency checks"""
    req = SlabAllocRequestData(origin="req", name="cacheA")
    obj = SlabAllocObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    slab = SlabAllocSlabData(
        origin="slab",
        addr=common_data["page_addr"],
        name="cacheA"
    )
    
    # 1. Empty request name (Line 59: if not req.name)
    req_empty = SlabAllocRequestData(origin="req", name="")
    with pytest.raises(AssertionError, match="Name mismatch"):
        SlabAllocMsg(req_empty, obj)

    # 2. Slab name mismatch (Line 59: req.name != slab.name)
    slab_wrong = SlabAllocSlabData(
        origin="slab",
        addr=common_data["page_addr"],
        name="cacheB"
    )
    with pytest.raises(AssertionError, match="Name mismatch"):
        SlabAllocMsg(req, slab_wrong, obj)

    # 3. Object name mismatch (Line 59: req.name != obj.name)
    obj_wrong = SlabAllocObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="cacheB",
        slab_addr=common_data["page_addr"]
    )
    with pytest.raises(AssertionError, match="Name mismatch"):
        SlabAllocMsg(req, obj_wrong)

def test_alloc_msg_address_checks(common_data):
    """Line 62-65: Address validation"""
    req = SlabAllocRequestData(origin="req", name="cacheA")
    obj = SlabAllocObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    
    # Slab address 0 (Line 62)
    slab_zero = SlabAllocSlabData(
        origin="slab",
        addr=0,
        name="cacheA"
    )
    with pytest.raises(AssertionError, match="Slab address mismatch"):
        SlabAllocMsg(req, slab_zero, obj)

    # Slab address mismatch (Line 62)
    slab_diff = SlabAllocSlabData(
        origin="slab",
        addr=common_data["diff_page_addr"],
        name="cacheA"
    )
    with pytest.raises(AssertionError, match="Slab address mismatch"):
        SlabAllocMsg(req, slab_diff, obj)

    # Object address 0 (Line 64)
    obj_zero = SlabAllocObjData(
        origin="obj",
        addr=0,
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    with pytest.raises(AssertionError, match="Invalid object address"):
        SlabAllocMsg(req, obj_zero)

    # Object not in page (Line 64)
    obj_far = SlabAllocObjData(
        origin="obj",
        addr=common_data["diff_page_addr"],
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    with pytest.raises(AssertionError, match="Invalid object address"):
        SlabAllocMsg(req, obj_far)

# --- Test SlabFreeMsg ---

def test_free_msg_arg_count_and_type(common_data):
    """Line 71: Arg count and type check"""
    obj = SlabFreeObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    
    # Too few args (0)
    with pytest.raises(AssertionError, match="Expected 1-2 lines"):
        SlabFreeMsg()
        
    # Too many args (3)
    with pytest.raises(AssertionError, match="Expected 1-2 lines"):
        SlabFreeMsg(obj, obj, obj)
        
    # Wrong type
    with pytest.raises(AssertionError, match="Expected 1-2 lines"):
        SlabFreeMsg("Not a FreeObjData")

def test_free_msg_names(common_data):
    """Line 77: Name validation"""
    # Empty object name
    obj_empty = SlabFreeObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="",
        slab_addr=common_data["page_addr"]
    )
    with pytest.raises(AssertionError, match="Name mismatch"):
        SlabFreeMsg(obj_empty)
        
    # Name mismatch with Slab
    obj = SlabFreeObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    slab_wrong = SlabFreeSlabData(
        origin="slab",
        addr=common_data["page_addr"],
        name="cacheB"
    )
    with pytest.raises(AssertionError, match="Name mismatch"):
        SlabFreeMsg(obj, slab_wrong)

def test_free_msg_addresses(common_data):
    """Line 79, 81: Address validation"""
    obj = SlabFreeObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    
    # Invalid Slab addr (Line 79)
    slab_zero = SlabFreeSlabData(
        origin="slab",
        addr=0,
        name="cacheA"
    )
    with pytest.raises(AssertionError, match="Invalid slab to free"):
        SlabFreeMsg(obj, slab_zero)
        
    # Obj addr 0 (Line 81)
    obj_zero = SlabFreeObjData(
        origin="obj",
        addr=0,
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    with pytest.raises(AssertionError, match="Invalid obj_addr"):
        SlabFreeMsg(obj_zero)
        
    # Obj not in same page (Line 81)
    obj_far = SlabFreeObjData(
        origin="obj",
        addr=common_data["diff_page_addr"],
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    with pytest.raises(AssertionError, match="Invalid obj_addr"):
        SlabFreeMsg(obj_far)

# --- Test SlabPrintMsg ---

def test_print_msg():
    """Line 90, 92-93: check() and __repr__"""
    # Using kwargs for clarity and correctness
    data = SlabPrintfKmemStatusData(
        origin="raw",
        addr=0x1000,
        name="cache",
        object_size=64,
        in_cache_obj=0
    )
    msg = SlabPrintMsg(data)
    
    # Trigger __repr__ (Line 92-93)
    repr_str = repr(msg)
    assert "SlabPrintMsg" in repr_str
    assert "raw" in repr_str

# --- Test ListCheckMsg ---

def test_list_check_msg():
    """Line 97: super().check()"""
    msg = ListCheckMsg("some data")
    
    # Should not raise exception
    msg.check()