from ctypes import c_int64
from trax_aarch64_asm import AArch64Assembler, RelocVar
from trax_backend import AppleSiliconBackend, Backend
from trax_obj import TraxObject

def test_basic_aarch64_function():
    # Create an AArch64Assembler instance
    asm = AArch64Assembler()

    # Generate assembly code to double the input
    # TODO: Fix this!!!!
    asm.ldr(2, 0, imm=0)
    asm.ldr(3, 0, imm=8)
    asm.add(0, 2, 3)    # Add x0 to itself and store in x0
    asm.ret()           # Return from the function

    # Get the bytes of the generated code
    code_bytes = asm.to_bytes()

    be = Backend.apple_silicon()

    # Create executable memory
    addr = be.create_executable_memory(code_bytes)

    # Convert memory to a function
    ct = be.const_table([])
    gaurd_id, values_to_keep = be.call_function(addr, [TraxObject.from_int(5), TraxObject.from_int(9)], ct)

    # Check if the result is correct
    assert TraxObject(c_int64(gaurd_id)).to_int() == 14  # 5 + 9 = 14

def test_aarch64_loop():
    asm = AArch64Assembler()

    # Initialize counter (x0) to 0
    asm.mov(2, 31)  # x31 is XZR (zero register)

    # Initialize sum (x1) to 0
    asm.mov(3, 31)

    # We need 1 and 10 as constants
    asm.ldr(4, 0, imm=0)
    asm.ldr(5, 0, imm=8)

    # Loop start label
    loop_start = RelocVar()
    asm.assign_label(loop_start)
    asm.add(3, 3, 2)
    asm.add(2, 2, 4)
    asm.cmp(2, 5)
    asm.blt(loop_start)
    asm.mov(0, 3)
    asm.ret()

    # Get the bytes of the generated code
    code_bytes = asm.to_bytes()
    print("Code bytes:", code_bytes.hex())
    import sys
    sys.stdout.flush()

    be = Backend.apple_silicon()

    # Create executable memory
    addr = be.create_executable_memory(code_bytes)

    # Call the function
    ct = be.const_table([])
    result = be.call_function(addr, [TraxObject.from_int(1), TraxObject.from_int(11)], ct)

    # Check if the result is correct (sum of numbers from 0 to 9)
    assert result.to_int() == 55
