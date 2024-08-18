from trax_ast import *
from trax_bc_compile import Compiler

def test_compile_square_method():
    ast = [
        Method('Int', 'square', [],
            Block([
                ExprStmt(MethodCall(Qualified(['self']), '*', [Qualified(['self'])]))
            ]))
    ]
    compiler = Compiler(ast)
    constants, method_map = compiler.compile()
    assert len(method_map) == 1
    assert (0, 'square') in method_map
    instructions = method_map[(0, 'square')]
    assert len(instructions) == 6
    assert instructions[0]['opcode'] == 'dup'
    assert instructions[1]['opcode'] == 'dup'
    assert instructions[2]['method_name'] == '*'
    assert instructions[3]['opcode'] == 'pop'
    assert instructions[4]['opcode'] == 'push_const'
    assert instructions[5]['opcode'] == 'return'

def test_compile_square_method_with_return():
    ast = [
        Method('Int', 'square', [],
            Block([
                Return(MethodCall(Qualified(['self']), '*', [Qualified(['self'])]))
            ]))
    ]
    compiler = Compiler(ast)
    constants, method_map = compiler.compile()
    assert len(method_map) == 1
    assert (0, 'square') in method_map
    instructions = method_map[(0, 'square')]
    assert len(instructions) == 6
    assert instructions[0]['opcode'] == 'dup'
    assert instructions[1]['opcode'] == 'dup'
    assert instructions[2]['method_name'] == '*'
    assert instructions[3]['opcode'] == 'return'
    assert instructions[4]['opcode'] == 'push_const'
    assert instructions[5]['opcode'] == 'return'
