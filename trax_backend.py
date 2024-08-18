import mmap
import ctypes as ct
import sys
import os
from trax_aarch64_asm import AArch64Assembler
from trax_obj import TraxObject
from trax_tracing import *

class Backend:
    def create_executable_memory(self, code_bytes: bytes):
        raise NotImplementedError("Subclasses must implement create_executable_memory")

    def const_table(self, consts: list[TraxObject]):
        raise NotImplementedError("Subclasses must implement const_table")

    def call_function(self, func_ptr, args: list[TraxObject], const_table, return_buffer_size: int):
        raise NotImplementedError("Subclasses must implement call_function")

    def compile_trace(self, trace_compiler: TraceCompiler, const_table):
        raise NotImplementedError("Subclasses must implement compile_trace")

    @staticmethod
    def apple_silicon():
        return AppleSiliconBackend()

# NOTE: Nice to haves later
#         > spill the inputs to a different register in the preamble (backend specific)
#         > allocate anything needed for spills (backend specific)
#         > add instruction for small constants

class AppleSiliconBackend(Backend):
    def __init__(self):
        self.libc = ct.CDLL(None)

        self.malloc = self.libc.malloc
        self.malloc.restype = ct.c_void_p
        self.malloc.argtypes = (ct.c_size_t,)

    def create_executable_memory(self, code_bytes):
        page_size = mmap.PAGESIZE
        code_size = len(code_bytes)
        aligned_size = (code_size + page_size - 1) & ~(page_size - 1)

        mmap_function = self.libc.mmap
        mmap_function.restype = ct.c_void_p
        mmap_function.argtypes = (ct.c_void_p, ct.c_size_t, ct.c_int, ct.c_int, ct.c_int, ct.c_longlong)

        mprotect_function = self.libc.mprotect
        mprotect_function.restype = ct.c_int
        mprotect_function.argtypes = (ct.c_void_p, ct.c_size_t, ct.c_int)

        # Use libc.mmap instead of Python's mmap
        addr = mmap_function(
            ct.c_void_p(0),
            aligned_size,
            3,
            4098,
            -1,
            0
        )

        if addr == 18446744073709551615:
            errno = ct.c_int.in_dll(self.libc, "errno")
            raise OSError(os.strerror(errno.value))

        # Copy code to the allocated memory
        ct.memmove(addr, code_bytes, len(code_bytes))

        # Change memory protection to executable
        err = mprotect_function(addr, aligned_size, mmap.PROT_EXEC | mmap.PROT_READ)
        if err == -1:
            errno = ct.c_int.in_dll(self.libc, "errno")
            raise OSError(os.strerror(errno.value))

        return addr

    def const_table(self, consts: list[TraxObject]):
        if not consts:
            return ct.cast(0, ct.POINTER(ct.c_int64))

        const_table = self.malloc(ct.sizeof(ct.c_int64) * (1 + len(consts)))
        const_table = ct.cast(const_table, ct.POINTER(ct.c_int64))
        for i, value in enumerate(consts):
            const_table[i] = value.value
        # We need to inject malloc in here somewhere for now
        const_table[len(consts)] = ct.addressof(self.malloc)

        return const_table

    def allocate(self, size: int):
        return self.malloc(ct.sizeof(ct.c_int64) * size)

    def new(self, type_index: int, values: list[TraxObject]) -> TraxObject:
        ptr = self.malloc(ct.sizeof(ct.c_int64) * (1 + len(values)))
        ptr = ct.cast(ptr, ct.POINTER(ct.c_int64))
        ptr[0] = ct.c_int64(type_index)
        for i, value in enumerate(values):
            ptr[i+1] = value.value

        v = ct.cast(ptr, ct.c_void_p).value
        return TraxObject(ct.c_int64(v if v is not None else 0))

    def call_function(self, func_ptr, args: list[TraxObject], const_table, return_buffer_size: int = 0):
        # Create a function pointer type
        func_type = ct.CFUNCTYPE(ct.c_int, ct.POINTER(ct.c_int64), ct.POINTER(ct.c_int64), ct.POINTER(ct.c_int64))
        #func_type = ffi.typeof("int(*)(trax_value*, trax_value*, trax_value*)")

        # construct inputs
        if return_buffer_size == 0:
            ret_buf = ct.cast(ct.c_int(0), ct.POINTER(ct.c_int64))
        else:
            ret_buf = self.allocate(return_buffer_size)
        ptr = self.allocate(len(args))
        for i, value in enumerate(args):
            ptr[i] = value.value

        # Cast the address to a function pointer
        func_ptr = ct.cast(func_ptr, func_type)

        return_value = int(func_ptr(ptr, const_table, ret_buf))
        # TODO: free shit
        return_values = []
        for i in range(return_buffer_size):
            return_values.append(TraxObject(ret_buf[i]))

        return return_value, return_values

    # TODO TODO TODO: This needs to be tested!!!
    def compile_trace(self, trace_compiler: TraceCompiler, const_table):
        from trax_aarch64_asm import AArch64Assembler, RelocVar

        asm = AArch64Assembler()

        # Create RelocVars for all guard exits
        guard_exits = {inst.guard_id: RelocVar() for inst in trace_compiler.get_instructions() if isinstance(inst, GuardInstruction)}

        # Perform register allocation
        allowed_registers = [3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 8, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]
        instructions = trace_compiler.preamble + trace_compiler.body
        register_allocation = allocate_registers(instructions, allowed_registers)

        # Find all registers that are caller-save and used
        used_caller_save = set(register_allocation.values()) & set([8, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28])
        stack_size = len(used_caller_save) * 8

        # Save caller-save registers
        if stack_size > 0:
            asm.sub_imm(31, 31, stack_size)
        for i, reg in enumerate(used_caller_save):
            asm.str(reg, 31, imm=i * 8)

        # Compile the preamble first
        for inst in trace_compiler.preamble:
            self._compile_instruction(asm, inst, register_allocation, guard_exits)

        # Create a RelocVar for the trace entry point
        trace_entry = RelocVar()
        asm.assign_label(trace_entry)
        for inst in trace_compiler.body:
            self._compile_instruction(asm, inst, register_allocation, guard_exits)

        # Handle any movs needed for phi nodes
        for input_inst in trace_compiler.body:
            if not isinstance(input_inst, InputInstruction):
                continue
            rd = register_allocation[input_inst] # This is about to be live
            rm = register_allocation[input_inst.phi] # This is assured to be live
            # Do not emit a mov if we don't have to
            if rd != rm:
                asm.mov(rd, rm)
        asm.b(trace_entry)

        # Create a RelocVar for the final cleanup
        final_cleanup = RelocVar()

        # Compile guard exits
        for guard_inst in instructions:
            if not isinstance(guard_inst, GuardInstruction):
                continue

            guard_id = guard_inst.guard_id
            exit_label = guard_exits[guard_id]

            asm.assign_label(exit_label)

            # Store values in the return buffer
            for i, value in enumerate(guard_inst.values_to_keep):
                asm.str(register_allocation[value], 2, imm=i * 8) # x2 points to the return buffer

            # Set x0 to the guard_id
            asm.mov_imm(0, imm=guard_id)

            # Jump to final cleanup
            asm.b(final_cleanup)

        # Final cleanup
        asm.assign_label(final_cleanup)

        # Restore caller-save registers
        for i, reg in enumerate(used_caller_save):
            asm.ldr(reg, 31, i * 8)
        if stack_size > 0:
            asm.add_imm(31, 31, stack_size)

        asm.ret()

        return asm.to_bytes()

    # TODO: Things would be a lot better if we used high-order pointer tagging instead
    def _compile_instruction(self, asm: AArch64Assembler, inst, register_allocation, guard_exits):
        if isinstance(inst, GuardInstruction):
            reg = register_allocation[inst.operand]
            if isinstance(inst, GuardInt):
                asm.ands(31, reg, immr=0, imms=0)
                asm.bne(guard_exits[inst.guard_id])
            elif isinstance(inst, GuardNil):
                asm.ands(17, reg, immr=0, imms=2)
                asm.cmp_imm(17, TraxObject.NIL_TAG)
                asm.bne(guard_exits[inst.guard_id])
            elif isinstance(inst, GuardTrue):
                asm.ands(17, reg, immr=0, imms=2)
                asm.cmp_imm(17, TraxObject.TRUE_TAG)
                asm.bne(guard_exits[inst.guard_id])
            elif isinstance(inst, GuardBool):
                asm.ands(17, reg, immr=0, imms=1)
                asm.cmp_imm(17, imm=0b11)
                asm.bne(guard_exits[inst.guard_id])
            elif isinstance(inst, GuardIndex):
                asm.ands(16, reg, immr=60, imms=60)
                asm.ldr(16, 16) # Load as early as possible
                asm.ands(17, reg, immr=0, imms=2) # Follow up with parallel inst
                asm.cmp_imm(17, TraxObject.OBJECT_TAG) # Do some compute while loading
                asm.bne(guard_exits[inst.guard_id]) # Should be ~free
                asm.cmp_imm(16, inst.type_index) # After load is  done one more cycle
                asm.bne(guard_exits[inst.guard_id]) # Should be ~free
            elif isinstance(inst, GuardLT):
                reg2 = register_allocation[inst.right]
                asm.cmp(reg, reg2)
                asm.bge(guard_exits[inst.guard_id])
            elif isinstance(inst, GuardLE):
                reg2 = register_allocation[inst.right]
                asm.cmp(reg, reg2)
                asm.bgt(guard_exits[inst.guard_id])
            elif isinstance(inst, GuardGT):
                reg2 = register_allocation[inst.right]
                asm.cmp(reg, reg2)
                asm.ble(guard_exits[inst.guard_id])
            elif isinstance(inst, GuardGE):
                reg2 = register_allocation[inst.right]
                asm.cmp(reg, reg2)
                asm.blt(guard_exits[inst.guard_id])
            elif isinstance(inst, GuardEQ):
                reg2 = register_allocation[inst.right]
                asm.cmp(reg, reg2)
                asm.bne(guard_exits[inst.guard_id])
            elif isinstance(inst, GuardNE):
                reg2 = register_allocation[inst.right]
                asm.cmp(reg, reg2)
                asm.beq(guard_exits[inst.guard_id])
            # Add more guard types as needed
        elif isinstance(inst, BinaryOpInstruction):
            rd = register_allocation[inst]
            rn = register_allocation[inst.left]
            rm = register_allocation[inst.right]
            if isinstance(inst, AddInstruction):
                asm.add(rd, rn, rm)
            elif isinstance(inst, SubInstruction):
                asm.sub(rd, rn, rm)
            elif isinstance(inst, LtInstruction):
                asm.mov_imm(17, imm=TraxObject.FALSE_TAG)
                asm.mov_imm(16, imm=TraxObject.TRUE_TAG)
                asm.cmp(rn, rm)
                asm.csel(rd, 16, 17, cond=AArch64Assembler.LT)
            # Add more binary operations as needed
        elif isinstance(inst, ConstantInstruction):
            rd = register_allocation[inst]
            asm.ldr(rd, 1, inst.constant_index * 8) # x1 points to const array
        elif isinstance(inst, InputInstruction):
            rd = register_allocation[inst]
            asm.ldr(rd, 0, inst.input_index * 8) # x0 points to inputs array
            pass
        elif isinstance(inst, CopyInstruction):
            rd = register_allocation[inst.input]
            rm = register_allocation[inst.value]
            if rd != rm:
                asm.mov(rd, rm)
            pass
        else:
            raise NotImplemented(f"No implementation for {type(inst)} in {type(self)}")
        # Add more instruction types as needed
