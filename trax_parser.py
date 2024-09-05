"""
grammar of trax-lang:

top -> (struct | method)*
struct -> 'struct' id '{' field* '}'
field -> id ';'
method -> 'fn' id ':' id '(' arglist ')' block
arglist -> id | id ',' arglist
block -> '{' stmt '}'
stmt -> for_loop | while_loop | if_stmt | assign | var_decl | ret_stmt | (expr ';')
ret_stmt -> 'return' expr ';'
var_decl -> 'var' id '=' expr ';'
for_loop -> 'for' id 'in' expr block
while_loop -> 'while' expr block
if_stmt -> 'if' expr block
         | 'if' expr block 'else' block
assign -> qualified '=' expr ';'
expr -> prim (id arg)*
prim -> '(' expr ')' | id | int | new_expr
new_expr -> 'new' id '{' exprlist? '}'
arg -> '(' exprlist? ')' | qualified
qualified -> id ('.' id)*
exprlist -> expr
          | expr ',' exprlist

"""

import re
from typing import Generator
from trax_ast import *
from trax_obj import TraxObject

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> list[AST]:
        return self.parse_top()

    def src_info(self):
        token = self.tokens[self.current]
        return src_loc(token.line, token.col)

    @staticmethod
    def with_src_info(func):
        def inner(self, *args):
            with self.src_info():
                return func(*args)
        return func

    def parse_top(self) -> list[AST]:
        nodes: list[AST] = []
        while self.current < len(self.tokens):
            with self.src_info():
                if self.match('struct'):
                    nodes.append(self.parse_struct())
                elif self.match('fn'):
                    nodes.append(self.parse_method())
                else:
                    raise SyntaxError(f"Unexpected token: {self.tokens[self.current]}")
        return nodes

    @with_src_info
    def parse_struct(self) -> Struct:
        self.consume('struct')
        name = self.consume('id')
        self.consume('{')
        fields = []
        while not self.match('}'):
            fields.append(self.parse_field())
        self.consume('}')
        return Struct(name, fields)

    @with_src_info
    def parse_field(self) -> Field:
        name = self.consume('id')
        self.consume(';')
        return Field(name)

    @with_src_info
    def parse_method(self) -> Method:
        self.consume('fn')
        class_name = self.consume('id')
        self.consume(':')
        method_name = self.consume('id')
        self.consume('(')
        args = self.parse_arglist()
        self.consume(')')
        body = self.parse_block()
        return Method(class_name, method_name, args, body)

    def parse_arglist(self) -> list[str]:
        args = []
        if not self.match(')'):
            args.append(self.consume('id'))
            while self.match(','):
                self.consume(',')
                args.append(self.consume('id'))
        return args

    @with_src_info
    def parse_block(self) -> Block:
        self.consume('{')
        stmts = []
        while not self.match('}'):
            stmts.append(self.parse_stmt())
        self.consume('}')
        return Block(stmts)

    def parse_stmt(self) -> Stmt:
        if self.match('for'):
            return self.parse_for_loop()
        elif self.match('while'):
            return self.parse_while_loop()
        elif self.match('if'):
            return self.parse_if_stmt()
        elif self.match('var'):
            return self.parse_var_decl()
        elif self.match('return'):
            return self.parse_return_stmt()
        elif self.match('id'):
            with self.src_info():
                qualified = self.parse_qualified()
                if self.match('='):
                    return self.parse_assign(qualified)
                else:
                    expr = self.parse_expr_continue(qualified)
                    self.consume(';')
                    return ExprStmt(expr)
        else:
            expr = self.parse_expr()
            self.consume(';')
            return ExprStmt(expr)

    @with_src_info
    def parse_for_loop(self) -> ForLoop:
        self.consume('for')
        var = self.consume('id')
        self.consume('in')
        iterable = self.parse_expr()
        body = self.parse_block()
        return ForLoop(var, iterable, body)

    @with_src_info
    def parse_while_loop(self) -> WhileLoop:
        self.consume('while')
        condition = self.parse_expr()
        body = self.parse_block()
        return WhileLoop(condition, body)

    @with_src_info
    def parse_if_stmt(self) -> If | IfElse:
        self.consume('if')
        condition = self.parse_expr()
        if_body = self.parse_block()
        if self.match('else'):
            self.consume('else')
            else_body = self.parse_block()
            return IfElse(condition, if_body, else_body)
        return If(condition, if_body)

    @with_src_info
    def parse_var_decl(self) -> VarDecl:
        self.consume('var')
        name = self.consume('id')
        self.consume('=')
        expr = self.parse_expr()
        self.consume(';')
        return VarDecl(name, expr)

    @with_src_info
    def parse_return_stmt(self) -> Return:
        self.consume('return')
        expr = self.parse_expr()
        self.consume(';')
        return Return(expr)

    def parse_assign(self, qualified) -> Assign:
        self.consume('=')
        expr = self.parse_expr()
        self.consume(';')
        return Assign(qualified, expr)

    def parse_expr(self) -> Expr:
        expr = self.parse_prim()
        return self.parse_expr_continue(expr)

    def parse_expr_continue(self, expr) -> Expr:
        while self.match('id'):
            method = self.consume('id')
            arg = self.parse_arg()
            expr = MethodCall(expr, method, arg)
        return expr

    @with_src_info
    def parse_prim(self) -> Expr:
        if self.match('('):
            self.consume('(')
            expr = self.parse_expr()
            self.consume(')')
            return expr
        elif self.match('num'):
            v = int(self.consume('num'))
            return Constant(TraxObject.from_int(v))
        elif self.match('new'):
            return self.parse_new_expr()
        return self.parse_qualified()

    @with_src_info
    def parse_new_expr(self) -> Expr:
        self.consume('new')
        class_name = self.consume('id')
        self.consume('{')
        if self.match('}'):
            self.consume('}')
            return NewExpr(class_name, [])
        args = self.parse_exprlist()
        self.consume('}')
        return NewExpr(class_name, args)

    @with_src_info
    def parse_qualified(self) -> Qualified:
        qualified = [self.consume('id')]
        while self.match('.'):
            self.consume('.')
            qualified.append(self.consume('id'))
        return Qualified(qualified)

    @with_src_info
    def parse_arg(self) -> list[Expr]:
        if self.match('('):
            self.consume('(')
            if self.match(')'):
                self.consume(')')
                return []
            args = self.parse_exprlist()
            self.consume(')')
            return args

        if self.match('num'):
            v = int(self.consume('num'))
            return [Constant(TraxObject.from_int(v))]

        return [self.parse_qualified()]

    def parse_exprlist(self) -> list[Expr]:
        exprs = [self.parse_expr()]
        while self.match(','):
            self.consume(',')
            exprs.append(self.parse_expr())
        return exprs

    def match(self, expected_type, offset=0) -> bool:
        if self.current + offset >= len(self.tokens):
            return False
        return self.tokens[self.current + offset].type == expected_type

    def consume(self, expected_type) -> str:
        if self.match(expected_type):
            token = self.tokens[self.current]
            self.current += 1
            return token.value
        start = max(0, self.current - 5)
        to_show = self.tokens[start:self.current+5]
        to_show = [str(t) for t in to_show]
        raise SyntaxError(f"Expected {expected_type}, tokens[{start - self.current}:5]={to_show}, got {self.tokens[self.current].type}")

from dataclasses import dataclass

@dataclass
class Token:
    type: str
    value: str
    line: int
    col: int

    def __str__(self):
        return f"{self.type}:{self.value}"

def tokenize(code) -> Generator[Token]:
    keywords = {'return', 'struct', 'var', 'fn', 'for', 'in', 'while', 'if', 'else', '=', '.', 'new'}
    token_specification = [
        ('id',    r'[A-Za-z_][A-Za-z0-9_]*|[~!@#$%^&*\-+=\[\]<>.?/]+'),
        ('num',   r'\d+(\.\d*)?'),
        ('paren', r'[()]'),
        ('brace', r'[{}]'),
        ('punct', r'[,;:]'),
        ('skip',  r'[ \t\n]+'),
    ]
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
    matches = list(re.finditer(tok_regex, code))
    line = 1
    col = 1
    for i, mo in enumerate(matches):
        kind = mo.lastgroup
        value = mo.group()
        if kind == 'skip':
            newlines = value.count('\n')
            if newlines > 0:
                line += newlines
                col = len(value) - value.rfind('\n')
            else:
                col += len(value)
            continue
        if kind == 'id' and value in keywords:
            kind = value
        elif kind in ['paren', 'brace', 'punct', 'assign']:
            kind = value
        assert kind is not None
        yield Token(kind, value, line, col)
        col += len(value)
        if i == len(matches) - 1 and mo.end() < len(code):
            raise ValueError(f"Tokenization error: Unexpected character '{code[mo.end()]}' at line {line}, column {col}")

def parse(code):
    tokens = list(tokenize(code))
    #print([str(t) for t in tokens])
    parser = Parser(tokens)
    return parser.parse()
