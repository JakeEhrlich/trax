from trax_ast import *
from trax_parser import parse
from trax_bc_compile import Compiler
from trax_interp import Interpreter
from trax_obj import TraxObject
from trax_tracing import TraceCompiler, ValueInstruction
from trax_runtime import DefaultRuntime

def test_interpret_pair_swap():
    code = """
    struct Pair {
        first;
        second;
    }
    fn Pair:swap() {
        var temp = self.first;
        self.first = self.second;
        self.second = temp;
        return self;
    }
    """
    ast = parse(code)
    compiler = Compiler(ast)
    constants, method_map = compiler.compile()

    interpreter = Interpreter(constants, method_map)


    # Create a pair object with values 5 and 10
    pair = interpreter.backend.new(3, [TraxObject.from_int(5), TraxObject.from_int(10)])

    # Run the interpreter with the 'swap' method and the pair object
    result = interpreter.run(pair, 'swap')

    # The result should be a pair with swapped values
    assert result.is_object()
    assert result.get_field(0).to_int() == 10
    assert result.get_field(1).to_int() == 5

def test_interpret_int_swap_pair():
    code = """
    struct Pair {
        first;
        second;
    }
    fn Pair:swap() {
        var temp = self.first;
        self.first = self.second;
        self.second = temp;
        return self;
    }
    fn Int:swap_pair(other) {
        var pair = new Pair{self, other};
        pair swap();
        return pair;
    }
    """
    ast = parse(code)
    compiler = Compiler(ast)
    constants, method_map = compiler.compile()

    interpreter = Interpreter(constants, method_map)
    DefaultRuntime.add_methods_to_interpreter(interpreter)

    # Create two integer objects with values 5 and 10
    int1 = TraxObject.from_int(5)
    int2 = TraxObject.from_int(10)

    # Run the interpreter with the 'swap_pair' method and the two integer objects
    result = interpreter.run(int1, 'swap_pair', int2)

    # The result should be a pair with swapped values
    assert result.is_object()
    assert result.get_field(0).to_int() == 10
    assert result.get_field(1).to_int() == 5


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
    DefaultRuntime.add_methods_to_interpreter(interpreter)

    # Add '*' method for integers
    def int_multiply(stack):
        b = stack.pop()
        a = stack.pop()
        if not (a.is_integer() and b.is_integer()):
            raise ValueError("Both operands must be integers")
        result = a.to_int() * b.to_int()
        return TraxObject.from_int(result)

    def int_multiply_trace(tc: TraceCompiler, args: list[ValueInstruction]):
        return tc.mul(args[0], args[1])

    #interpreter.add_builtin_method(0, '*', int_multiply, int_multiply_trace)

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
    DefaultRuntime.add_methods_to_interpreter(interpreter)

    input_value = TraxObject.from_int(101)
    result = interpreter.run(input_value, 'sum_to')

    assert result.is_integer()
    assert result.to_int() == 5050  # Sum of numbers from 1 to 99

def test_gravler_sim():
    code = """
    struct Rng {
        state;
    }
    fn Rng:sample() {
        self.state = (self.state * 16807) & 4294967295;
        return self.state;
    }
    fn Rng:roll() {
        var i = 1;
        var count = 0;
        while i < 231 {
            count = count + ((self sample() & 3 == 0) to_int());
            i = i + 1;
        }
    }
    fn Int:gravler_sim() {
        var rng = new Rng{594676966};
        var i = 1;
        var max_roll = 0;
        while i < self {
            max_roll = max_roll max (rng roll());
            i = i + 1;
        }
        return max_roll;
    }
    """
    ast = parse(code)
    compiler = Compiler(ast)
    constants, method_map = compiler.compile()

    interpreter = Interpreter(constants, method_map)
    DefaultRuntime.add_methods_to_interpreter(interpreter)

    input_value = TraxObject.from_int(101)
    result = interpreter.run(input_value, 'gravler_sim')

    assert result.is_integer()
    assert result.to_int() == 5050  # Sum of numbers from 1 to 99
