# TODO: We're asssuming little endian here but ideally we'd allow
#       for big endian as well...still only like router use big endian
#       so lets ignore that for now
class Relocation:
    def __init__(self, offset: int, size: int, func):
        self.offset = offset
        self.size = size
        self.func = func

    @staticmethod
    def instruction(offset, func):
        def wrapper_func(bytes):
            inst = int.from_bytes(bytes, byteorder='little')
            new_inst: int = func(inst)
            return new_inst.to_bytes(4, byteorder='little')

        return Relocation(offset, 4, wrapper_func)

    def apply(self, bytes: bytearray):
        sub = bytes[self.offset:(self.offset + self.size)]
        new_sub = self.func(sub)
        bytes[self.offset:(self.offset + self.size)] = new_sub

class RelocVar:
    def __init__(self):
        self.value = 0

class AArch64Assembler:
    # Condition codes
    EQ = 0  # Equal
    NE = 1  # Not equal
    GE = 10 # Greater than or equal
    LT = 11 # Less than
    GT = 12 # Greater than
    LE = 13 # Less than or equal

    def __init__(self):
        self.code = bytearray()
        self.relocations = []

    def assign_label(self, var: RelocVar):
        var.value = len(self.code)

    def _append_instruction(self, instruction):
        self.code.extend(instruction.to_bytes(4, byteorder='little'))

    def add(self, rd, rn, rm):
        instruction = 0x8B000000 | (rm << 16) | (rn << 5) | rd
        self._append_instruction(instruction)

    def sub(self, rd, rn, rm):
        instruction = 0xCB000000 | (rm << 16) | (rn << 5) | rd
        self._append_instruction(instruction)

    def sub_imm(self, rd, rn, imm):
        assert 0 <= imm < 4096
        instruction = 0xD1000000 | (imm << 10) | (rn << 5) | rd
        self._append_instruction(instruction)

    def add_imm(self, rd, rn, imm):
        assert 0 <= imm < 4096
        instruction = 0x91000000 | (imm << 10) | (rn << 5) | rd
        self._append_instruction(instruction)

    def cmp(self, rn, rm):
        instruction = 0xEB000000 | (rm << 16) | (rn << 5) | 0x1F
        self._append_instruction(instruction)

    def cmp_imm(self, rn, imm):
        assert 0 <= imm < 4096
        instruction = 0xF1000000 | (imm << 10) | (rn << 5) | 0x1F
        self._append_instruction(instruction)

    def mov(self, rd, rm):
        instruction = 0xAA0003E0 | (rm << 16) | rd
        self._append_instruction(instruction)

    def mov_imm(self, rd, imm):
        assert 0 <= imm < 65536
        instruction = 0xD2800000 | (imm << 5) | rd
        self._append_instruction(instruction)

    def ldr(self, rt, rn, imm=0):
        assert imm % 8 == 0
        instruction = 0xF9400000 | ((imm >> 3) << 10) | (rn << 5) | rt
        self._append_instruction(instruction)

    def str(self, rt, rn, imm=0):
        assert imm % 8 == 0
        instruction = 0xF9000000 | ((imm >> 3) << 10) | (rn << 5) | rt
        self._append_instruction(instruction)

    def b(self, label: RelocVar):
        current_offset = len(self.code)
        def reloc_func(inst):
            # TODO: there could be an off by 1 error here
            assert current_offset % 4 == 0
            assert label.value % 4 == 0
            offset = label.value - current_offset
            return inst | ((offset >> 2) & 0x3FFFFFF)
        self.relocations.append(Relocation.instruction(current_offset, reloc_func))
        self._append_instruction(0x14000000)

    def _b_cond(self, cond, label: RelocVar):
        current_offset = len(self.code)
        def reloc_func(inst):
            assert current_offset % 4 == 0
            assert label.value % 4 == 0
            offset = label.value - current_offset
            print(f"{offset=}", current_offset, label.value)
            return inst | (((offset >> 2) & 0x7FFFF) << 5)
        self.relocations.append(Relocation.instruction(current_offset, reloc_func))
        instruction = 0x54000000 | (cond & 0xF)
        self._append_instruction(instruction)

    def beq(self, label: RelocVar):
        self._b_cond(self.EQ, label)

    def bne(self, label: RelocVar):
        self._b_cond(self.NE, label)

    def bge(self, label: RelocVar):
        self._b_cond(self.GE, label)

    def blt(self, label: RelocVar):
        self._b_cond(self.LT, label)

    def bgt(self, label: RelocVar):
        self._b_cond(self.GT, label)

    def ble(self, label: RelocVar):
        self._b_cond(self.LE, label)

    def ret(self):
        instruction = 0xD65F03C0
        self._append_instruction(instruction)

    def add_data(self, data):
        if isinstance(data, int):
            self.code.extend(data.to_bytes(4, byteorder='little'))
        elif isinstance(data, bytes):
            self.code.extend(data)
        else:
            raise ValueError("Data must be int or bytes")

    def to_bytes(self):
        for reloc in self.relocations:
            reloc.apply(self.code)
        return bytes(self.code)

    def and_imm(self, rd, rn, imm):
        assert 0 <= imm < 4096
        instruction = 0x92000000 | (imm << 10) | (rn << 5) | rd
        self._append_instruction(instruction)

    def lsl(self, rd, rn, shift):
        assert 0 <= shift < 64
        instruction = 0xD3400000 | ((64 - shift) << 16) | (rn << 5) | rd
        self._append_instruction(instruction)

    def lsr(self, rd, rn, shift):
        assert 0 <= shift < 64
        instruction = 0xD3400000 | (shift << 16) | (rn << 5) | rd
        self._append_instruction(instruction)

    def asr(self, rd, rn, shift):
        assert 0 <= shift < 64
        instruction = 0x93400000 | (shift << 16) | (rn << 5) | rd
        self._append_instruction(instruction)

    def ands(self, rd, rn, immr, imms):
        assert 0 <= immr < 64 and 0 <= imms < 64
        instruction = 0xF2000000 | (immr << 16) | (imms << 10) | (rn << 5) | rd | (1 << 22)
        self._append_instruction(instruction)

    def eor(self, rd, rn, rm):
        instruction = 0xCA000000 | (rm << 16) | (rn << 5) | rd
        self._append_instruction(instruction)

    def csel(self, rd, rn, rm, cond):
        instruction = 0x9A800000 | (rm << 16) | (cond << 12) | (rn << 5) | rd
        self._append_instruction(instruction)
