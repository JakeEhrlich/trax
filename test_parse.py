from trax_ast import *
from trax_parser import parse

def test_parse_struct():
    code = """
    struct Point {
        x;
        y;
    }
    """
    result = parse(code)
    assert result == [Struct('Point', [Field('x'), Field('y')])]

def test_parse_return_stmt():
    code = """
    fn Int:square() {
        return self * self;
    }
    """
    result = parse(code)
    assert result == [Method('Int', 'square', [],
                       Block([
                           Return(MethodCall(Qualified(['self']), '*', [Qualified(['self'])]))
                       ]))]

def test_parse_method():
    code = """
    fn Point:new(x, y) {
        self.x = x;
        self.y = y;
    }
    """
    result = parse(code)
    assert result == [Method('Point', 'new', ['x', 'y'],
                       Block([
                           Assign(Qualified(['self', 'x']), Qualified(['x'])),
                           Assign(Qualified(['self', 'y']), Qualified(['y']))
                       ]))]

def test_parse_for_loop():
    code = """
    fn List:map(f) {
        for item in self {
            f call(item);
        }
    }
    """
    result = parse(code)
    assert result == [Method('List', 'map', ['f'],
                       Block([
                           ForLoop('item', Qualified(['self']),
                            Block([
                                ExprStmt(MethodCall(Qualified(['f']), 'call', [Qualified(['item'])]))
                            ]))
                       ]))]

def test_parse_if_else():
    code = """
    fn Int:max(b) {
        if self > b {
            self;
        } else {
            b;
        }
    }
    """
    result = parse(code)
    assert result == [Method('Int', 'max', ['b'],
                       Block([
                           IfElse(
                            MethodCall(Qualified(['self']), '>', [Qualified(['b'])]),
                            Block([ExprStmt(Qualified(['self']))]),
                            Block([ExprStmt(Qualified(['b']))]))
                       ]))]
