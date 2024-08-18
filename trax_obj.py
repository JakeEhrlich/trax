from cffi import FFI

ffi = FFI()
ffi.cdef("""
    typedef int64_t trax_value;
""")

class TraxObject:
    INTEGER_TAG = 0b000
    NIL_TAG = 0b001
    OBJECT_TAG = 0b101
    FALSE_TAG = 0b011
    TRUE_TAG = 0b111

    nil = ffi.cast("trax_value", NIL_TAG)
    true = ffi.cast("trax_value", TRUE_TAG)
    false = ffi.cast("trax_value", FALSE_TAG)

    @staticmethod
    def from_int(value):
        return TraxObject(ffi.cast("trax_value", value << 1))

    def to_int(self):
        assert self.is_integer()
        return int(self.value) >> 1

    def __init__(self, value):
        self.value = ffi.cast("trax_value", value)

    def is_integer(self):
        return (int(self.value) & 0b1) == 0

    def is_nil(self):
        return (int(self.value) & 0b111) == self.NIL_TAG

    def is_true(self):
        return (int(self.value) & 0b111) == self.TRUE_TAG

    def is_false(self):
        return (int(self.value) & 0b111) == self.FALSE_TAG

    def is_boolean(self):
        return self.is_true() or self.is_false()

    def is_object(self):
        return (int(self.value) & 0b111) == self.OBJECT_TAG

    def get_object_address(self):
        if not self.is_object():
            raise ValueError("Not an object")
        return int(self.value) & 0xFFFFFFFFFFFFFFF8  # Mask out the lowest 3 bits

    def get_type_index(self):
        if self.is_integer():
            return 0
        elif self.is_boolean():
            return 1
        elif self.is_nil():
            return 2
        elif self.is_object():
            ptr = ffi.cast("trax_value *", self.get_object_address())
            return int(ptr[0])
        else:
            raise ValueError("Unknown object type")

    def __repr__(self):
        if self.is_integer():
            return f"Integer({int(self.value) >> 1})"
        elif self.is_nil():
            return "Nil"
        elif self.is_true():
            return "True"
        elif self.is_false():
            return "False"
        elif self.is_object():
            return f"Object(address=0x{self.get_object_address():x}, type={self.get_type_index()})"
        else:
            return f"Unknown(0x{int(self.value):x})"

    @staticmethod
    def new(type_index, values):
        size = (len(values) + 1) * ffi.sizeof("trax_value")
        ptr = ffi.new(f"trax_value[{len(values) + 1}]")
        ptr[0] = ffi.cast("trax_value", type_index)
        for i, value in enumerate(values, 1):
            ptr[i] = value.value
        iptr = ffi.cast("trax_value", ptr)
        iptr_tag = int(iptr) | TraxObject.OBJECT_TAG
        return TraxObject(ffi.cast("trax_value", iptr_tag))

    @staticmethod
    def free(obj):
        if not obj.is_object():
            raise ValueError("Cannot free a non-object")
        ptr = ffi.cast("trax_value *", obj.get_object_address())
        ffi.release(ptr)

    def get_field(self, field_index):
        if not self.is_object():
            raise ValueError("Cannot get field of a non-object")
        ptr = ffi.cast("trax_value *", self.get_object_address())
        return TraxObject(ptr[field_index + 1])

    def set_field(self, field_index, value):
        if not self.is_object():
            raise ValueError("Cannot set field of a non-object")
        ptr = ffi.cast("trax_value *", self.get_object_address())
        ptr[field_index + 1] = value.value
