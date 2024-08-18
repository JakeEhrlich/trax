from trax_ast import *
from trax_parser import parse
from trax_bc_compile import Compiler
from trax_interp import Interpreter
from trax_obj import TraxObject
from trax_tracing import TraceCompiler, ValueInstruction

def test_interpret_square_method():
    ast = [
        Method('Int', 'square', [],
            Block([
                Return(MethodCall(Qualified(['self']), '*', [Qualified(['self'])]))
            ]))
    ]
    compiler = Compiler(ast)
    constants, method_map = compiler.compile()

    interpreter = Interpreter(constants, method_map)

    # Add '*' method for integers
    def int_multiply(stack):
        b = stack.pop()
        a = stack.pop()
        if not (a.is_integer() and b.is_integer()):
            raise ValueError("Both operands must be integers")
        result = (int(a.value) >> 1) * (int(b.value) >> 1)
        return TraxObject(result << 1)

    def int_multiply_trace(tc: TraceCompiler, args: list[ValueInstruction]):
        return tc.mul(args[0], args[1])

    interpreter.add_builtin_method(0, '*', int_multiply, int_multiply_trace)

    # Create an integer object with value 5
    input_value = TraxObject.from_int(5)

    # Run the interpreter with the 'square' method and input value
    result = interpreter.run(input_value, 'square')

    # The result should be 25 (5^2)
    assert result.is_integer()
    assert result.to_int() == 25

def test_interpret_sum_to_100():
    code = """
    fn Int:sum_to() {
        var sum = 0;
        var i = 1;
        while i < self {
            sum = sum + i;
            i = i + 1;
        }
        return sum;
    }
    """
    ast = parse(code)
    compiler = Compiler(ast)
    constants, method_map = compiler.compile()

    interpreter = Interpreter(constants, method_map)

    def int_add(stack):
        b = stack.pop()
        a = stack.pop()
        if not (a.is_integer() and b.is_integer()):
            raise ValueError("Both operands must be integers")
        result = int(a.value) + int(b.value)
        return TraxObject(result)

    def int_add_trace(tc: Interpreter, args: list[ValueInstruction]):
        tc.emit_guard_index(args[0], 0)
        tc.emit_guard_index(args[1], 0)
        return tc.trace_compiler.add(args[0], args[1])

    def int_less(stack):
        b = stack.pop()
        a = stack.pop()
        if not (a.is_integer() and b.is_integer()):
            raise ValueError("Both operands must be integers")
        result = int(a.value) < int(b.value)
        return TraxObject(TraxObject.TRUE_TAG if result else TraxObject.FALSE_TAG)

    def int_less_trace(tc: Interpreter, args: list[ValueInstruction]):
        tc.emit_guard_index(args[0], 0)
        tc.emit_guard_index(args[1], 0)
        return tc.trace_compiler.lt(args[0], args[1])

    interpreter.add_builtin_method(0, '+', int_add, int_add_trace)
    interpreter.add_builtin_method(0, '<', int_less, int_less_trace)

    input_value = TraxObject.from_int(101)
    result = interpreter.run(input_value, 'sum_to')

    assert result.is_integer()
    assert result.to_int() == 5050  # Sum of numbers from 1 to 99
