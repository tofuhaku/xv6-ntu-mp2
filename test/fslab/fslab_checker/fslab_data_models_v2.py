from dataclasses import dataclass
from typing import Any, Literal, Set, Union, List, Dict, Optional, Tuple

from .fslab_utils_v2 import hex_to_int, is_in_same_page

# 64 bit for xv6 system
MAX_ADDR_64BIT = (1 << 64) - 1

# Ensure address is in range
def validate_addr_range(val: int, field_name: str):
    """Helper to validate address range."""
    # [Robustness] Ensure val is int before comparison
    if not isinstance(val, int):
        raise TypeError(f"{field_name} must be int, got {type(val).__name__}")
    
    if val < 0:
        raise ValueError(f"{field_name} cannot be negative: {val}")
    if val > MAX_ADDR_64BIT:
        raise ValueError(f"{field_name} exceeds 64-bit limit: 0x{val:x}")

@dataclass
class BaseData:
    """Base class for all slab-related data with original string representation."""
    origin: str
    def __str__(self) -> str:
        return self.origin

# Abstract base class: Data structure with address
@dataclass
class AddrData:
    """Base class for data structures with an address field."""
    addr: Union[str, int]
    def __post_init__(self):
        if isinstance(self.addr, str):
            self.addr = hex_to_int(self.addr)
        
        validate_addr_range(self.addr, "Address")

# --- Concrete Log Data Structures ---

@dataclass
class SlabCreateData(BaseData, AddrData):
    """Data for a newly created slab cache."""
    name: str
    object_size: int
    max_objs: int
    in_cache_obj: int
    def __post_init__(self):
        super().__post_init__()
        self.object_size = int(self.object_size)
        self.max_objs = int(self.max_objs)
        self.in_cache_obj = int(self.in_cache_obj)
        
        # Ensure object variables are positive
        if self.object_size <= 0:
            raise ValueError(f"Invalid object_size: {self.object_size} (must be > 0)")
        
        if self.max_objs <= 0:
            raise ValueError(f"Invalid max_objs: {self.max_objs} (must be > 0)")
            
        if self.in_cache_obj < 0:
            raise ValueError(f"Invalid in_cache_obj: {self.in_cache_obj} (must be >= 0)")

@dataclass
class SlabAllocRequestData(BaseData):
    name: str

@dataclass
class SlabAllocSlabData(BaseData, AddrData):
    name: str
    # addr: int

@dataclass
class SlabAllocObjData(BaseData, AddrData):
    name: str
    slab_addr: int
    # addr: int
    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.slab_addr, str):
            self.slab_addr = hex_to_int(self.slab_addr)
            
        validate_addr_range(self.slab_addr, "slab_addr")

@dataclass
class SlabFreeObjData(BaseData, AddrData):
    name: str
    slab_addr: int
    # addr: int
    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.slab_addr, str):
            self.slab_addr = hex_to_int(self.slab_addr)
            
        validate_addr_range(self.slab_addr, "slab_addr")

@dataclass
class SlabFreeSlabData(BaseData, AddrData):
    name: str
    # addr: int

@dataclass
class SlabPrintfKmemStatusData(BaseData, AddrData):
    name: str
    object_size: int
    # addr: int
    in_cache_obj: int
    def __post_init__(self):
        super().__post_init__()
        self.object_size = int(self.object_size)
        self.in_cache_obj = int(self.in_cache_obj)

SlabType = Literal['full', 'partial', 'free', 'cache']

@dataclass
class SlabPrintfSlabListStatusData(BaseData):
    slab_type: SlabType

@dataclass
class SlabPrintfSlabStatusData(BaseData, AddrData):
    # addr: int
    freelist: int
    nxt: int
    def __post_init__(self):
        super().__post_init__()     # Call super for 'addr' validation
        
        if isinstance(self.freelist, str):
            self.freelist = hex_to_int(self.freelist)
        if isinstance(self.nxt, str):
            self.nxt = hex_to_int(self.nxt)
        
        validate_addr_range(self.freelist, "freelist")
        validate_addr_range(self.nxt, "nxt")

class SlabPrinfEndData(BaseData):
    pass

@dataclass
class SlabPrintfObjStatusData(BaseData, AddrData):
    idx: int
    # addr: int
    as_ptr: int
    as_obj: dict
    def __post_init__(self):
        super().__post_init__()
        self.idx = int(self.idx)
        self.as_ptr = hex_to_int(self.as_ptr)
        
        if isinstance(self.as_ptr, str):
            self.as_ptr = hex_to_int(self.as_ptr)
            
        validate_addr_range(self.as_ptr, "as_ptr")

@dataclass
class ListCheckData(BaseData):
    init: int
    _add: int
    _del: int
    def __post_init__(self):
        # BaseData has no definition for __post_init__
        # super().__post_init__()
        if isinstance(self.init, str):
            self.init = int(self.init)
        if isinstance(self._add, str):
            self._add = int(self._add)
        if isinstance(self._del, str):
            self._del = int(self._del)


# --- Simulator State Models ---

class Obj:
    def __init__(self, obj_addr: int):
        self.addr = obj_addr
        self.allocated = False
        
    # Implement __eq__ and __hash__, use addr as the only identifier
    def __eq__(self, other):
        """
        Equality check based on address.
        Two objects are considered equal if they point to the same memory address.
        """
        if not isinstance(other, Obj):
            return NotImplemented
        return self.addr == other.addr

    def __hash__(self):
        """
        Hash based on address to support set operations.
        """
        return hash(self.addr)

    def __str__(self) -> str:
        return f"Obj(addr=0x{self.addr:x}, allocated={self.allocated})"

class Slab:
    def __init__(self, slab_addr: int, max_objs: int):
        self.addr = slab_addr
        self.max_objs = max_objs
        # --- Improvement F: Set objs to private, prevent overflow ---
        self._objs: Dict[int, Obj] = {}
        
    @property
    def objs(self) -> Dict[int, Obj]:
        """Read-Only property to access the objects in the slab."""
        return self._objs.copy()
    
    # --- Improvement B: add add_obj to check max_objs ---
    def add_obj(self, obj: Obj) -> None:
        """
        Add objects to slab safely and check max_objs.
        """
        if obj.addr not in self._objs:
            # Check only when adding new object
            if len(self._objs) >= self.max_objs:
                raise ValueError(
                    f"Slab capacity exceeded: max {self.max_objs},"
                    f"current {len(self._objs)}. Cannot add 0x{obj.addr:x}"
                )
        self._objs[obj.addr] = obj
    
    def get_obj(self, addr: int) ->  Optional[Obj]:
        return self._objs.get(addr)
        
    def count_avail_objs(self) -> int:
        # Count on self._objs
        return len([o for o in self._objs.values() if not o.allocated]) + (self.max_objs - len(self._objs))
    # --------------------------

    def __str__(self) -> str:
        lines = [
            f"\tSlab(addr=0x{self.addr:x})",
            f"  Objects ({len(self.objs)}):",
        ]
        if not self.objs:
            lines.append("    None")
        else:
            for obj_addr, obj in self.objs.items():
                lines.append(f"    0x{obj_addr:x}: {obj}")
        return "\n\t\t".join(lines)

class KmemCache:
    def __init__(self, name: str, obj_size: int,
                 addr: int, max_objs: int, in_cache_obj: int):
        self.name: str = name
        self.obj_size: int = obj_size
        self.addr: int = addr
        self.max_objs: int = max_objs
        self.in_cache_obj: int = in_cache_obj
        # --- Improvement C: Initialize as set() ---
        self.objs: Set[Obj] = set()
        self.full: Dict[int, Slab] = {}
        self.partial: Dict[int, Slab] = {}
        self.free: Dict[int, Slab] = {}
        
        if self.in_cache_obj != 0:
            # Dummy address i * obj_size
            self.objs = { Obj(i * self.obj_size) for i in range(self.in_cache_obj) }

    def __str__(self) -> str:
        lines = [
            f"KmemCache: {self.name}",
            f"  Addr       : 0x{self.addr:x}",
            f"  Object Size: {self.obj_size}",
            f"  Max Objects: {self.max_objs}",
            f"  Cache Slab:",
        ]
        if not self.objs:
            lines.append("    None")
        else:
            for obj in self.objs:
                lines.append(f"    {obj}")
        lines.append(f"  Full Slabs ({len(self.full)}):")
        for slab in self.full.values():
            lines.append(f"{slab}")
        lines.append(f"  Partial Slabs ({len(self.partial)}):")
        for slab in self.partial.values():
            lines.append(f"{slab}")
        lines.append(f"  Free Slabs ({len(self.free)}):")
        for slab in self.free.values():
            lines.append(f"{slab}")
        return "\n".join(lines)

    def count_allocated_objs(self):
        res = 0
        res += len(list(filter(lambda o: o.allocated, self.objs)))
        # Use set() and eq/hash, calculate is more precise
        for slab in (*self.full.values(), *self.partial.values(), *self.free.values()):
            # Access through self.objs (return .copy()).
            # Or directly access self._objs if allow friend access.
            res += len(list(filter(lambda o: o.allocated, slab.objs.values())))
        return res