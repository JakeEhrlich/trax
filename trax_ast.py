import contextlib
from trax_obj import TraxObject
from dataclasses import dataclass

@dataclass
class SourceLocation:
    line: int
    column: int

    def __str__(self):
        return f"line {self.line}, column {self.column}"

_location_stack = []

@contextlib.contextmanager
def src_loc(line, column):
    _location_stack.append(SourceLocation(line, column))
    try:
        yield
    finally:
        _location_stack.pop()

def get_current_location():
    return _location_stack[-1] if _location_stack else SourceLocation(0, 0)

class AST:
    def __init__(self):
        self.location = get_current_location()

class Expr(AST):
    pass

class Stmt(AST):
    pass

@dataclass
class Struct(AST):
    name: str
    fields: list['Field']

    def __post_init__(self):
        super().__init__()

@dataclass
class Field(AST):
    name: str

    def __post_init__(self):
        super().__init__()

@dataclass
class Method(AST):
    class_name: str
    method_name: str
    args: list[str]
    body: 'Block'

    def __post_init__(self):
        super().__init__()

@dataclass
class Block(AST):
    stmts: list[Stmt]

    def __post_init__(self):
        super().__init__()

@dataclass
class Assign(Stmt):
    qualified: 'Qualified'
    expr: Expr

    def __post_init__(self):
        super().__init__()

@dataclass
class ExprStmt(Stmt):
    expr: Expr

    def __post_init__(self):
        super().__init__()

@dataclass
class If(Stmt):
    condition: Expr
    if_body: 'Block'

    def __post_init__(self):
        super().__init__()

@dataclass
class IfElse(Stmt):
    condition: Expr
    if_body: 'Block'
    else_body: 'Block'

    def __post_init__(self):
        super().__init__()

@dataclass
class ForLoop(Stmt):
    var: str
    iterable: Expr
    body: 'Block'

    def __post_init__(self):
        super().__init__()

@dataclass
class WhileLoop(Stmt):
    condition: Expr
    body: 'Block'

    def __post_init__(self):
        super().__init__()

@dataclass
class VarDecl(Stmt):
    name: str
    expr: Expr

    def __post_init__(self):
        super().__init__()

@dataclass
class Return(Stmt):
    expr: Expr

    def __post_init__(self):
        super().__init__()

@dataclass
class Qualified(Expr):
    names: list[str]

    def __post_init__(self):
        super().__init__()

@dataclass
class NewExpr(Expr):
    class_name: str
    args: list[Expr]

    def __post_init__(self):
        super().__init__()

@dataclass
class MethodCall(Expr):
    obj: Expr
    method: str
    args: list[Expr]

    def __post_init__(self):
        super().__init__()

@dataclass
class Constant(Expr):
    value: TraxObject

    def __post_init__(self):
        super().__init__()
