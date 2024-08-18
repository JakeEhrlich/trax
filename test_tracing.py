from trax_tracing import *

def test_trace_compiler():
    compiler = TraceCompiler()

    # Example trace: guard that x is an int, y is an int, then compute x + y * 2
    x_input = compiler.input(0)
    y_input = compiler.input(1)
    compiler.guard_int('guard1', x_input, [x_input, y_input])
    compiler.guard_int('guard2', y_input, [x_input, y_input])
    temp = compiler.add(y_input, y_input)
    result = compiler.add(x_input, temp)

    trace = compiler.get_instructions()
