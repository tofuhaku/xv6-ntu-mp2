import pytest
from fslab_checker import fslab_data_models as models

# fix in fslab_data_models.py line 115
# --- Hotfix for Bug in fslab_data_models.py ---
# def fixed_list_check_post_init(self):
#     if isinstance(self.init, str):
#         self.init = int(self.init)
#     if isinstance(self._add, str):
#         self._add = int(self._add)
#     if isinstance(self._del, str):
#         self._del = int(self._del)

# models.ListCheckData.__post_init__ = fixed_list_check_post_init
# ----------------------------------------------

# --- Tests for BaseData & AddrData ---

def test_basedata_str():
    origin = "some log line"
    data = models.BaseData(origin=origin)
    assert str(data) == origin

def test_addrdata_hex_conversion():
    data = models.AddrData(addr="0x1A")
    assert data.addr == 26

def test_addrdata_int_passthrough():
    data = models.AddrData(addr=100)
    assert data.addr == 100

# --- Tests for SlabCreateData ---

def test_slab_create_data():
    data = models.SlabCreateData(
        origin="origin_str",
        addr="0x1000",
        name="test_cache",
        object_size="32",
        max_objs="128",
        in_cache_obj="1"
    )
    assert data.addr == 4096
    assert data.object_size == 32
    assert data.max_objs == 128
    assert data.in_cache_obj == 1
    assert data.name == "test_cache"

# --- Tests for Alloc/Free Data ---

def test_slab_alloc_obj_data():
    data = models.SlabAllocObjData(
        origin="alloc_log",
        name="cache1",
        slab_addr="0x2000",
        addr="0x2020"
    )
    assert data.slab_addr == 8192
    assert data.addr == 8224

def test_slab_free_obj_data():
    data = models.SlabFreeObjData(
        origin="free_log",
        name="cache1",
        slab_addr="0x3000",
        addr="0x3030"
    )
    assert data.slab_addr == 12288
    assert data.addr == 12336

# --- Tests for Printf Status Data ---

def test_slab_printf_kmem_status():
    data = models.SlabPrintfKmemStatusData(
        origin="status",
        name="test",
        object_size="64",
        addr="0x4000",
        in_cache_obj="0"
    )
    assert data.object_size == 64
    assert data.in_cache_obj == 0
    assert data.addr == 16384

def test_slab_printf_obj_status():
    data = models.SlabPrintfObjStatusData(
        origin="obj_status",
        idx="5",
        addr="0x5000",
        as_ptr="0x5000",
        as_obj={'val': 1}
    )
    assert data.idx == 5
    assert data.addr == 20480
    assert data.as_ptr == 20480
    assert data.as_obj == {'val': 1}

# --- Tests for ListCheckData ---

def test_list_check_data():
    data = models.ListCheckData("list_check", "1", "2", "3")
    assert data.init == 1
    assert data._add == 2
    assert data._del == 3


# --- Tests for Simulator Models (Obj, Slab, KmemCache) ---

def test_obj_model():
    obj = models.Obj(obj_addr=0x100)
    assert obj.addr == 0x100
    assert obj.allocated is False
    assert "Obj(addr=0x100, allocated=False)" in str(obj)

    obj.allocated = True
    assert obj.allocated is True

def test_slab_model_logic():
    slab = models.Slab(slab_addr=0x2000, max_objs=10)
    assert slab.count_avail_objs() == 10

    obj1 = models.Obj(0x2020)
    obj1.allocated = True
    slab.objs[0x2020] = obj1
    assert slab.count_avail_objs() == 9

def test_slab_str_representation():
    slab = models.Slab(slab_addr=0x1000, max_objs=10)
    s_empty = str(slab)
    assert "Slab(addr=0x1000)" in s_empty
    assert "None" in s_empty

    obj = models.Obj(0x1020)
    slab.objs[0x1020] = obj
    s_filled = str(slab)
    assert "0x1020: Obj" in s_filled
    assert "None" not in s_filled

def test_kmem_cache_init_with_objs():
    cache = models.KmemCache(
        name="meta_cache", obj_size=32, addr=0x5000, max_objs=10, in_cache_obj=5
    )
    assert len(cache.objs) == 5
    assert any(o.addr == 0 for o in cache.objs)

def test_kmem_cache_str_representation():
    cache = models.KmemCache(
        name="complex_cache", obj_size=32, addr=0x8000, max_objs=10, in_cache_obj=2
    )
    slab_full = models.Slab(0xA000, 10)
    slab_partial = models.Slab(0xB000, 10)
    slab_free = models.Slab(0xC000, 10)

    cache.full[0xA000] = slab_full
    cache.partial[0xB000] = slab_partial
    cache.free[0xC000] = slab_free

    output = str(cache)

    assert "KmemCache: complex_cache" in output
    assert "Addr       : 0x8000" in output
    assert "Obj(addr=0x0" in output
    assert "Full Slabs (1):" in output
    assert "Slab(addr=0xa000)" in output
    assert "Partial Slabs (1):" in output
    assert "Slab(addr=0xb000)" in output
    assert "Free Slabs (1):" in output
    assert "Slab(addr=0xc000)" in output

def test_kmem_cache_str_empty_objs():
    cache = models.KmemCache(
        name="empty_objs", obj_size=32, addr=0x9000, max_objs=10, in_cache_obj=0
    )
    output = str(cache)
    assert "Cache Slab:" in output
    assert "None" in output

def test_kmem_cache_count_allocated_objs_complex():
    """
    Test count_allocated_objs comprehensively covering:
    - Objects inside the cache (self.objs)
    - Objects inside Full slabs
    - Objects inside Partial slabs
    - Objects inside Free slabs
    """
    # 1. Setup Cache with on-cache objects
    cache = models.KmemCache(
        name="count_test", obj_size=32, addr=0x1000, max_objs=10, in_cache_obj=5
    )
    
    # Manually mark 2 in-cache objects as allocated
    # Convert set to list to index them
    cache_objs = list(cache.objs)
    cache_objs[0].allocated = True
    cache_objs[1].allocated = True
    
    # 2. Setup Full Slab (3 objects, all allocated)
    slab_full = models.Slab(0x2000, 10)
    for i in range(3):
        o = models.Obj(0x2000 + i*32)
        o.allocated = True
        slab_full.objs[o.addr] = o
    cache.full[0x2000] = slab_full

    # 3. Setup Partial Slab (3 objects, 1 allocated)
    slab_partial = models.Slab(0x3000, 10)
    o1 = models.Obj(0x3000)
    o1.allocated = True
    slab_partial.objs[o1.addr] = o1
    
    o2 = models.Obj(0x3020) # Not allocated
    slab_partial.objs[o2.addr] = o2
    
    o3 = models.Obj(0x3040) # Not allocated
    slab_partial.objs[o3.addr] = o3
    
    cache.partial[0x3000] = slab_partial

    # 4. Setup Free Slab (Has objects but arguably "free", testing logic counts them anyway)
    # Let's add 1 allocated object here to ensure the loop covers 'free' list
    slab_free = models.Slab(0x4000, 10)
    o_free = models.Obj(0x4000)
    o_free.allocated = True
    slab_free.objs[o_free.addr] = o_free
    
    cache.free[0x4000] = slab_free

    # Expected Total:
    # Cache Objs: 2
    # Full Slab:  3
    # Partial:    1
    # Free Slab:  1
    # Total:      7
    
    assert cache.count_allocated_objs() == 7
    
# --- OO Identity ---

def test_obj_oo_identity():
    """
    [OO] Test Identity of objects. Ensure that two objects
    with the same address are not considered the same Python object.
    """
    addr = 0x1000
    obj1 = models.Obj(addr)
    obj2 = models.Obj(addr) # another object with the same address

    # Verify they are not the same Python object ( with no override __eq__)
    assert obj1 != obj2
    
    # Verify if they are considered different elements when added to a set
    s = set()
    s.add(obj1)
    s.add(obj2)
    assert len(s) == 2 
    # When implementing interpreter, ensure that do not re-create objects.
    # Or ensure that __eq__ is implemented correctly.

# --- MRO and Inheritance Logic ---

def test_inheritance_post_init_order():
    """
    [OO + MRO] Verify whether the initialization logic executes correctly under multiple inheritance.
    SlabCreateData(BaseData, AddrData) -> Ensure hex_to_int in AddrData is executed.
    """
    # Intentionally pass Hex string to fields which require int:
        # Test SlabCreateData.__post_init__() conversion.
    # Simutaneously pass Hex string to fields addr:
        # Test AddrData.__post_init__() conversion.
    data = models.SlabCreateData(
        origin="raw",
        name="test",
        object_size="100",  # String -> Int
        max_objs="10",      # String -> Int
        in_cache_obj="0",   # String -> Int
        addr="0xFF"         # Hex String -> Int (via super().__post_init__)
    )
    
    # Check if all levels of __post_init__ are executed
    assert isinstance(data.object_size, int)
    assert data.object_size == 100
    
    assert isinstance(data.addr, int)
    assert data.addr == 255


# --- Invariant Violation --- 

def test_invariant_slab_object_count():
    """
    [Architecture/Quality] Verify Invariant:
    No matter how many objects are added or removed,
    the total number of objects in the Slab should not exceed max_objs.
    If this test fails, it indicates a flaw in data structure design that allows for over-allocation.
    """
    max_objs = 5
    slab = models.Slab(0x1000, max_objs)
    
    # Try to add 6 objects (exceeding max_objs)
    # This is testing whether the Model layer has protection mechanisms.
    for i in range(max_objs + 1):
        addr = 0x1000 + i * 32
        slab.objs[addr] = models.Obj(addr)
    
    # This is a failure test because current Slab class does not prevent this.
    # This proves that Testability helps you discover: defensive logic is scattered in Interpreter, not in Model (Low Cohesion).
    # You can report that: "Through this test, I found that Model lacks self-validation ability, which is a direction for future refactoring."
    assert len(slab.objs) <= max_objs, "Invariant violated: Slab holding more objects than capacity!"