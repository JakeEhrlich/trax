import ctypes as ct

class TraxObject:
    # We use lower order bits for pointer tagging
    # The lowest order bit if set means this is an integer
    # The remaining 4 possible casses are for nil, object, true, and false
    # The second lowest order bit being set means its a boolean
    INTEGER_TAG = 0b000
    NIL_TAG = 0b001
    OBJECT_TAG = 0b101
    FALSE_TAG = 0b011
    TRUE_TAG = 0b111

    nil = ct.c_int64(NIL_TAG)
    true = ct.c_int64(TRUE_TAG)
    false = ct.c_int64(FALSE_TAG)

    @staticmethod
    def from_int(value):
        assert type(value) is int
        return TraxObject(ct.c_int64(value << 1))

    @staticmethod
    def from_bool(value):
        assert value is True or value is False
        return TraxObject(TraxObject.true if value else TraxObject.false)

    def to_int(self):
        assert self.is_integer()
        return self.value.value >> 1

    def to_bool(self):
        assert self.is_boolean()
        return self.is_true()

    def __init__(self, value: ct.c_int64):
        assert type(value) is ct.c_int64
        self.value = value

    def is_integer(self):
        return (self.value.value & 0b1) == 0

    def is_nil(self):
        return (self.value.value & 0b111) == self.NIL_TAG

    def is_true(self):
        return (self.value.value & 0b111) == self.TRUE_TAG

    def is_false(self):
        return (self.value.value & 0b111) == self.FALSE_TAG

    def is_boolean(self):
        return self.is_true() or self.is_false()

    def is_object(self):
        return (self.value.value & 0b111) == self.OBJECT_TAG

    def get_object_address(self) -> int:
        if not self.is_object():
            raise ValueError("Not an object")
        return self.value.value & 0xFFFFFFFFFFFFFFF8  # Mask out the lowest 3 bits

    def get_obj_pointer(self):
        return ct.cast(self.get_object_address(), ct.POINTER(ct.c_int64))

    # TODO: This function has been the source of many bugs
    #       We should find a way to standardize these better
    def get_type_index(self):
        if self.is_integer():
            return 0
        elif self.is_boolean():
            return 2
        elif self.is_nil():
            return 1
        elif self.is_object():
            ptr = self.get_obj_pointer()
            return int(ptr[0])
        else:
            raise ValueError("Unknown object type")

    def __repr__(self):
        if self.is_integer():
            return f"Integer({self.value.value >> 1})"
        elif self.is_nil():
            return "Nil"
        elif self.is_true():
            return "True"
        elif self.is_false():
            return "False"
        elif self.is_object():
            return f"Object(address=0x{self.get_object_address():x}, type={self.get_type_index()})"
        else:
            return f"Unknown(0x{self.value.value:x})"

    def get_field(self, field_index):
        if not self.is_object():
            raise ValueError("Cannot get field of a non-object")
        v = self.get_obj_pointer()[field_index + 1]
        return TraxObject(ct.c_int64(v))

    def set_field(self, field_index, value):
        if not self.is_object():
            raise ValueError("Cannot set field of a non-object")
        self.get_obj_pointer()[field_index + 1] = value.value
