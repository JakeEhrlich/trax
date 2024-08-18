class AST:
    pass

class Struct(AST):
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields

    def __eq__(self, other):
        return isinstance(other, Struct) and self.name == other.name and self.fields == other.fields

class Field(AST):
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Field) and self.name == other.name

class Method(AST):
    def __init__(self, class_name, method_name, args, body):
        self.class_name = class_name
        self.method_name = method_name
        self.args = args
        self.body = body

    def __eq__(self, other):
        return isinstance(other, Method) and self.class_name == other.class_name and \
               self.method_name == other.method_name and self.args == other.args and self.body == other.body

class Block(AST):
    def __init__(self, stmts):
        self.stmts = stmts

    def __eq__(self, other):
        return isinstance(other, Block) and self.stmts == other.stmts

class Assign(AST):
    def __init__(self, qualified, expr):
        self.qualified = qualified
        self.expr = expr

    def __eq__(self, other):
        return isinstance(other, Assign) and self.qualified == other.qualified and self.expr == other.expr

class ExprStmt(AST):
    def __init__(self, expr):
        self.expr = expr

    def __eq__(self, other):
        return isinstance(other, ExprStmt) and self.expr == other.expr

class If(AST):
    def __init__(self, condition, if_body):
        self.condition = condition
        self.if_body = if_body

    def __eq__(self, other):
        return isinstance(other, If) and self.condition == other.condition and self.if_body == other.if_body

class IfElse(AST):
    def __init__(self, condition, if_body, else_body):
        self.condition = condition
        self.if_body = if_body
        self.else_body = else_body

    def __eq__(self, other):
        return isinstance(other, IfElse) and self.condition == other.condition and \
               self.if_body == other.if_body and self.else_body == other.else_body

class ForLoop(AST):
    def __init__(self, var, iterable, body):
        self.var = var
        self.iterable = iterable
        self.body = body

    def __eq__(self, other):
        return isinstance(other, ForLoop) and self.var == other.var and \
               self.iterable == other.iterable and self.body == other.body

class WhileLoop(AST):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def __eq__(self, other):
        return isinstance(other, WhileLoop) and self.condition == other.condition and self.body == other.body

class VarDecl(AST):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

    def __eq__(self, other):
        return isinstance(other, VarDecl) and self.name == other.name and self.expr == other.expr

class Return(AST):
    def __init__(self, expr):
        self.expr = expr

    def __eq__(self, other):
        return isinstance(other, Return) and self.expr == other.expr

class Qualified(AST):
    def __init__(self, names):
        self.names = names

    def __eq__(self, other):
        return isinstance(other, Qualified) and self.names == other.names

class NewExpr(AST):
    def __init__(self, class_name, args):
        self.class_name = class_name
        self.args = args

    def __eq__(self, other):
        return isinstance(other, NewExpr) and self.class_name == other.class_name and self.args == other.args

class MethodCall(AST):
    def __init__(self, obj, method, args):
        self.obj = obj
        self.method = method
        self.args = args

    def __eq__(self, other):
        return isinstance(other, MethodCall) and self.obj == other.obj and \
               self.method == other.method and self.args == other.args

class Constant(AST):
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, Constant) and self.value == other.value
