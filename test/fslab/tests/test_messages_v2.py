import pytest
from fslab_checker.fslab_messages_v2 import (
    SlabCreateMsg,
    SlabAllocMsg,
    SlabFreeMsg,
    SlabPrintMsg,
    ListCheckMsg
)
from fslab_checker.fslab_data_models_v2 import (
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

def test_alloc_msg_success_existing_slab(common_data):
    """Success with 2 lines (existing slab)."""
    # 2 lines: Request, Obj
    req = SlabAllocRequestData(origin="req", name="cacheA")
    obj = SlabAllocObjData(
        origin="obj",
        name="cacheA",
        slab_addr=common_data["page_addr"],
        addr=common_data["obj_addr"]
    )
    
    msg = SlabAllocMsg(req, obj)
    assert msg.name == "cacheA"
    assert msg.obj_addr == common_data["obj_addr"]
    assert not msg.allocate_new
    
def test_alloc_msg_success_new_slab(common_data):
    """Success with 3 lines (new slab)."""
    # 3 lines: Request, Slab, Obj
    req = SlabAllocRequestData(origin="req", name="cacheA")
    slab = SlabAllocSlabData(
        origin="slab",
        name="cacheA",
        addr=common_data["page_addr"]
    )
    obj = SlabAllocObjData(
        origin="obj",
        name="cacheA",
        slab_addr=common_data["page_addr"],
        addr=common_data["obj_addr"]
    )
    
    msg = SlabAllocMsg(req, slab, obj)
    assert msg.name == "cacheA"
    assert msg.obj_addr == common_data["obj_addr"]
    assert msg.allocate_new
    
def test_alloc_msg_failure_data_type():
    """Incorrect data model types."""
    # First line wrong
    with pytest.raises(AssertionError, match="First line must be SlabAllocRequestData"):
        SlabAllocMsg(SlabAllocObjData(origin="", name="", slab_addr=1, addr=1), SlabAllocObjData(origin="", name="", slab_addr=1, addr=1))
    
    # Last line wrong
    with pytest.raises(AssertionError, match="Last line must be SlabAllocObjData"):
        SlabAllocMsg(SlabAllocRequestData(origin="", name=""), SlabAllocSlabData(origin="", name="", addr=1))
        
    # Second line wrong for 3-line message
    req = SlabAllocRequestData(origin="", name="")
    obj = SlabAllocObjData(origin="", name="", slab_addr=1, addr=1)
    with pytest.raises(AssertionError, match="Second line must be SlabAllocSlabData"):
        SlabAllocMsg(req, SlabAllocRequestData(origin="", name=""), obj)

def test_alloc_msg_failure_name_mismatch(common_data):
    """Name mismatch."""
    req = SlabAllocRequestData(origin="req", name="cacheA")
    slab = SlabAllocSlabData(origin="slab", name="cacheB", addr=common_data["page_addr"])
    obj = SlabAllocObjData(
        origin="obj",
        name="cacheA",
        slab_addr=common_data["page_addr"],
        addr=common_data["obj_addr"]
    )
    
    with pytest.raises(AssertionError, match="Name mismatch"):
        SlabAllocMsg(req, slab, obj)

def test_alloc_msg_failure_invalid_address(common_data):
    """Invalid addresses (0 or not in same page)."""
    # Obj addr is 0
    req = SlabAllocRequestData(origin="req", name="cacheA")
    obj_zero = SlabAllocObjData(
        origin="obj",
        name="cacheA",
        slab_addr=common_data["page_addr"],
        addr=0
    )
    with pytest.raises(AssertionError, match="Allocated obj_addr cannot be 0"):
        SlabAllocMsg(req, obj_zero)

    # Slab addr is 0
    obj_zero_slab = SlabAllocObjData(
        origin="obj",
        name="cacheA",
        slab_addr=0,
        addr=common_data["obj_addr"]
    )
    with pytest.raises(AssertionError, match="Allocated slab_addr cannot be 0"):
        SlabAllocMsg(req, obj_zero_slab)
        
    # Obj not in same page as slab
    obj_diff_page = SlabAllocObjData(
        origin="obj",
        name="cacheA",
        slab_addr=common_data["page_addr"],
        addr=common_data["diff_page_addr"]
    )
    with pytest.raises(AssertionError, match="is not in the same page as slab"):
        SlabAllocMsg(req, obj_diff_page)
        
def test_alloc_msg_failure_new_slab_mismatch(common_data):
    """New slab data mismatches."""
    req = SlabAllocRequestData(origin="req", name="cacheA")
    slab = SlabAllocSlabData(
        origin="slab",
        name="cacheA",
        addr=common_data["page_addr"] # Correct slab address
    )
    
    # Slab addr mismatch
    obj_mismatch_slab = SlabAllocObjData(
        origin="obj",
        name="cacheA",
        slab_addr=common_data["diff_page_addr"],    # Object refers to a different slab
        addr=common_data["diff_page_addr"] + 0x20   # Keep obj in diff_page_addr page
    )
    with pytest.raises(AssertionError, match="Allocated slab_addr mismatch"):
        SlabAllocMsg(req, slab, obj_mismatch_slab)

    # Slab addr is 0
    slab_zero = SlabAllocSlabData(
        origin="slab",
        name="cacheA",
        addr=0
    )
    obj_zero_slab = SlabAllocObjData(
        origin="obj",
        name="cacheA",
        slab_addr=0,
        addr=common_data["obj_addr"]
    )
    with pytest.raises(AssertionError, match="Allocated slab_addr cannot be 0"):
        SlabAllocMsg(req, slab_zero, obj_zero_slab)

# --- Test SlabFreeMsg ---

def test_free_msg_success_obj_only(common_data):
    """Success with 1 line (free object)."""
    obj = SlabFreeObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    
    msg = SlabFreeMsg(obj)
    assert msg.name == "cacheA"
    assert msg.obj_addr == common_data["obj_addr"]
    assert msg.free_slab == 0

def test_free_msg_success_obj_and_slab(common_data):
    """Success with 2 lines (free object and slab)."""
    obj = SlabFreeObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    slab = SlabFreeSlabData(
        origin="slab",
        addr=common_data["page_addr"],
        name="cacheA"
    )
    
    msg = SlabFreeMsg(obj, slab)
    assert msg.name == "cacheA"
    assert msg.free_slab == common_data["page_addr"]

def test_free_msg_failure_data_type(common_data):
    """Incorrect data model types."""
    obj = SlabFreeObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    
    # First line wrong
    with pytest.raises(AssertionError, match="First line must be SlabFreeObjData"):
        SlabFreeMsg(SlabFreeSlabData(origin="", name="", addr=1))
        
    # Second line wrong
    with pytest.raises(AssertionError, match="Second line must be SlabFreeSlabData"):
        SlabFreeMsg(obj, SlabAllocObjData(origin="", name="", slab_addr=1, addr=1))

def test_free_msg_failure_name_mismatch(common_data):
    """Name mismatch."""
    obj = SlabFreeObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    slab = SlabFreeSlabData(
        origin="slab",
        addr=common_data["page_addr"],
        name="cacheB"
    )
    
    with pytest.raises(AssertionError, match="Name mismatch"):
        SlabFreeMsg(obj, slab)
        
def test_free_msg_failure_invalid_address(common_data):
    """Invalid addresses (0 or not in same page)."""
    
    # Obj addr is 0
    obj_zero_addr = SlabFreeObjData(
        origin="obj",
        addr=0,
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    with pytest.raises(AssertionError, match="Invalid obj_addr.*cannot be 0"):
        SlabFreeMsg(obj_zero_addr)
        
    # Slab addr is 0
    obj_zero_slab = SlabFreeObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="cacheA",
        slab_addr=0
    )
    with pytest.raises(AssertionError, match="Invalid.*slab_addr.*cannot be 0"):
        SlabFreeMsg(obj_zero_slab)
        
    # Obj not in same page as slab
    obj_far = SlabFreeObjData(
        origin="obj",
        addr=common_data["diff_page_addr"],
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    with pytest.raises(AssertionError, match="is not in the same page as slab"):
        SlabFreeMsg(obj_far)

def test_free_msg_failure_slab_to_free_mismatch(common_data):
    """Slab to free mismatch or 0."""
    obj = SlabFreeObjData(
        origin="obj",
        addr=common_data["obj_addr"],
        name="cacheA",
        slab_addr=common_data["page_addr"]
    )
    
    # Slab addr to free is 0
    slab_zero = SlabFreeSlabData(
        origin="slab",
        addr=0,
        name="cacheA"
    )
    with pytest.raises(AssertionError, match="Invalid slab addr to free"):
        SlabFreeMsg(obj, slab_zero)
        
    # Slab addr to free does not match object's slab_addr
    slab_mismatch = SlabFreeSlabData(
        origin="slab",
        addr=common_data["diff_page_addr"],
        name="cacheA"
    )
    with pytest.raises(AssertionError, match="Slab address mismatch"):
        SlabFreeMsg(obj, slab_mismatch)

# --- Test SlabPrintMsg ---

def test_print_msg():
    """check() and __repr__"""
    # Using kwargs for clarity and correctness
    data = SlabPrintfKmemStatusData(
        origin="raw",
        addr=0x1000,
        name="cache",
        object_size=64,
        in_cache_obj=0
    )
    msg = SlabPrintMsg(data)
    
    # Trigger __repr__
    repr_str = repr(msg)
    assert "SlabPrintMsg" in repr_str
    assert "raw" in repr_str

# --- Test ListCheckMsg ---

def test_list_check_msg():
    """super().check()"""
    msg = ListCheckMsg("some data")
    
    # Should not raise exception
    msg.check()