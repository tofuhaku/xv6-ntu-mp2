import abc
from enum import Enum
from typing import Union

from .fslab_utils_v2 import is_in_same_page
from .fslab_data_models_v2 import (
    SlabCreateData, SlabAllocRequestData, SlabAllocSlabData, SlabAllocObjData,
    SlabFreeObjData, SlabFreeSlabData
)

# Command base class
class MyMsg(abc.ABC):
    def __init__(self, *msg_data):
        self.msg_data = msg_data
        self.check()

    @abc.abstractmethod
    def check(self):
        """Validate the debug message data."""

    def bad_msg(self, msg: str):
        # Truncate data list for better error message
        data_snippet = str(self.msg_data)[:100] + '...' if len(str(self.msg_data)) > 100 else str(self.msg_data)
        raise AssertionError(f"Invalid {self.__class__.__name__}: {msg}\nData: {self.msg_data}")

    def __repr__(self):
        return f"{self.__class__.__name__} {self.msg_data}"

# Concrete debug message classes
class SlabCreateMsg(MyMsg):
    def check(self, valid_object_size: int = 504):
        if len(self.msg_data) != 1 or not isinstance(self.msg_data[0], SlabCreateData):
            self.bad_msg("Expected single SlabCreateData")
        data = self.msg_data[0]
        # TODO: Removed hardcoded object_size check for flexibility in parsing, 
        # as it is checked by SlabCreateData now. 
        if not data.name:
            self.bad_msg("Name cannot be empty")
        if data.object_size != valid_object_size:
            self.bad_msg(f"Invalid object_size {data.object_size}")
            
        self.name = data.name
        self.object_size = data.object_size
        self.addr = data.addr
        # self.max_objs = data.max_objs
        # self.in_cache_obj = data.in_cache_obj

class SlabAllocMsg(MyMsg):
    def check(self):
        # Expected 2 or 3 lines: Alloc Request, (optional) Alloc Slab, Alloc Object
        # Case 1: 2 lines (Alloc Request, Alloc Object) -> Use existing partial slab
        # Case 2: 3 lines (Alloc Request, Alloc Slab, Alloc Object) -> New slab allocated
        if not (2 <= len(self.msg_data) <= 3):
            self.bad_msg("Expected 2-3 data items")
            
        req = self.msg_data[0] 
        obj = self.msg_data[-1]     # The last one should be obj data
        
        # Data Type check
        if not isinstance(req, SlabAllocRequestData):
            self.bad_msg(f"First line must be SlabAllocRequestData, got {type(req)}")
        if not isinstance(obj, SlabAllocObjData):
            self.bad_msg(f"Last line must be SlabAllocObjData, got {type(obj)}")
        if len(self.msg_data) == 3 and not isinstance(self.msg_data[1], SlabAllocSlabData):
            self.bad_msg(f"Second line must be SlabAllocSlabData, got {type(self.msg_data[1])}")
        
        # Logical Validation
        slab = self.msg_data[1] if len(self.msg_data) == 3 else None
        
        # Name consistency check
        if req.name != obj.name or (slab and req.name != slab.name):
            self.bad_msg(f"Name mismatch: request={req.name}, slab={slab.name if slab else ''}, obj={obj.name}")
        
        # Address validation
        if obj.addr == 0:
            self.bad_msg("Allocated obj_addr cannot be 0")
        if obj.slab_addr == 0:
            self.bad_msg("Allocated slab_addr cannot be 0")
        
        if not is_in_same_page(obj.addr, obj.slab_addr):
            self.bad_msg(f"Allocated obj_addr 0x{obj.addr:x} is not in the same page as slab 0x{obj.slab_addr:x}")

        # Slab Check (if a new slab was allocated)
        if slab:
            if slab.addr != obj.slab_addr:
                self.bad_msg(f"Allocated slab_addr mismatch: {slab.addr} != {obj.slab_addr}")
            if slab.addr == 0:
                self.bad_msg("Allocated slab_addr cannot be 0")
        
        self.name = obj.name
        self.obj_addr = obj.addr
        self.slab_addr = obj.slab_addr
        self.allocate_new = len(self.msg_data) == 3

class SlabFreeMsg(MyMsg):
    def check(self):
        # Expect 1 or 2 lines: free obj, (optional) Free Slab
        if not (1 <= len(self.msg_data) <= 2):
            self.bad_msg(f"Expected 1 or 2 lines, got {len(self.msg_data)}")
            
        obj = self.msg_data[0]
        slab = self.msg_data[1] if len(self.msg_data) == 2 else None
        
        # Data Type Check
        if not isinstance(obj, SlabFreeObjData):
            self.bad_msg(f"First line must be SlabFreeObjData, got {type(obj)}")
        if slab and not isinstance(slab, SlabFreeSlabData):
            self.bad_msg(f"Second line must be SlabFreeSlabData, got {type(slab)}")
        
        # Logical Check
        if not obj.name or (slab and obj.name != slab.name):
            self.bad_msg(f"Name mismatch: {obj.name} {slab.name if slab else ''}")
            
        # Address Validation
        if obj.addr == 0 or obj.slab_addr == 0:
            self.bad_msg(f"Invalid obj_addr (0x{obj.addr:x}) or slab_addr (0x{obj.slab_addr:x}) cannot be 0")
        
        if not is_in_same_page(obj.addr, obj.slab_addr):
            self.bad_msg(f"Invalid obj_addr 0x{obj.addr:x} is not in the same page as slab 0x{obj.slab_addr:x}")
        
        # Slab Check (if a slab was freed)
        if slab:
            if slab.addr == 0:
                self.bad_msg("Invalid slab addr to free (must not be 0)")
            # Sanity check: the slab being freed must be the one containing the object
            if slab.addr != obj.slab_addr:
                self.bad_msg(f"Slab address mismatch: slab to free 0x{slab.addr:x} != object's slab 0x{obj.slab_addr:x}")

        self.name = obj.name
        self.obj_addr = obj.addr
        self.slab_addr = obj.slab_addr
        self.free_slab: int = slab.addr if len(self.msg_data) == 2 else 0

class SlabPrintMsg(MyMsg):
    def check(self):
        pass
    def __repr__(self):
        res = [f"{self.__class__.__name__}", *[str(data) for data in self.msg_data]]
        return "\n\t".join(res)

class ListCheckMsg(MyMsg):
    def check(self):
        return super().check()

# --- Other Message Types ---

SlabMsg = Union[SlabCreateMsg,
                SlabAllocMsg,
                SlabFreeMsg,
                SlabPrintMsg]

class FileMsg(Enum):
    Init = "fileinit"
    Alloc = "filealloc"
    Close = "fileclose"