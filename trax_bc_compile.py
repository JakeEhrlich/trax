import trax_ast as ast
from trax_obj import TraxObject
from dataclasses import dataclass
from collections import defaultdict
from trax_parser import get_current_location, src_loc, SourceLocation

class BB:
    def __init__(self, index):
        self.index = index

class Instruction:
    src_info: SourceLocation

    def __init__(self):
        self.src_info = get_current_location()

@dataclass
class PushConst(Instruction):
    constant: TraxObject

    def __post_init__(self):
        super().__init__()

# @dataclass
# class Dup(Instruction):
#     k: int

@dataclass
class Pop(Instruction):
    def __post_init__(self):
        super().__init__()

# @dataclass
# class Set(Instruction):
#     k: int

@dataclass
class Call(Instruction):
    method_name: str
    num_args: int

    def __post_init__(self):
        super().__init__()

@dataclass
class Jmp(Instruction):
    target: int | BB
    loop_back: bool = False

    def __post_init__(self):
        super().__init__()

@dataclass
class JmpIfNot(Instruction):
    target: int | BB

    def __post_init__(self):
        super().__init__()

@dataclass
class GetField(Instruction):
    field_index: int

    def __post_init__(self):
        super().__init__()

@dataclass
class SetField(Instruction):
    field_index: int

    def __post_init__(self):
        super().__init__()

@dataclass
class New(Instruction):
    type_index: int
    num_fields: int

    def __post_init__(self):
        super().__init__()

@dataclass
class Return(Instruction):
    def __post_init__(self):
        super().__init__()

@dataclass
class GetVar(Instruction):
    var_index: int

    def __post_init__(self):
        super().__init__()

@dataclass
class SetVar(Instruction):
    var_index: int

    def __post_init__(self):
        super().__init__()

class MethodBuilder:
    def __init__(self, typename, method_name):
        self.typename = typename
        self.method_name = method_name
        self.blocks = []
        self.new_block()
        self.current_block = self.blocks[0]

    def new_block(self):
        block = []
        self.blocks.append(block)
        return BB(len(self.blocks) - 1)

    def switch_block(self, bb):
        if 0 <= bb.index < len(self.blocks):
            self.current_block = self.blocks[bb.index]
        else:
            raise ValueError(f"Invalid block index: {bb.index}")

    def get_current_block(self):
        return self.current_block

    def add_instruction(self, instruction):
        self.current_block.append(instruction)

    def push_const(self, constant: TraxObject):
        self.add_instruction(PushConst(constant))

    # def dup(self, k):
    #     self.add_instruction(Dup(k))

    def pop(self):
        self.add_instruction(Pop())

    def set(self, var_index):
        self.add_instruction(SetVar(var_index))

    def get(self, var_index):
        self.add_instruction(GetVar(var_index))

    def call(self, method_name, num_args):
        self.add_instruction(Call(method_name, num_args))

    def jmp(self, bb, loop_back=False):
        self.add_instruction(Jmp(bb, loop_back))

    def jmp_if_not(self, bb):
        self.add_instruction(JmpIfNot(bb))

    def get_field(self, field_index):
        self.add_instruction(GetField(field_index))

    def set_field(self, field_index):
        self.add_instruction(SetField(field_index))

    def new(self, type_index, num_fields):
        self.add_instruction(New(type_index, num_fields))

    def return_(self):
        self.add_instruction(Return())

    def build(self):
        # First pass: calculate offsets for each block
        block_offsets = {}
        offset = 0
        for i, block in enumerate(self.blocks):
            block_offsets[i] = offset
            offset += len(block)

        # Second pass: build instructions and resolve jumps
        instructions = []
        for i, block in enumerate(self.blocks):
            for instruction in block:
                if isinstance(instruction, (Jmp, JmpIfNot)):
                    assert isinstance(instruction.target, BB)
                    target_block = instruction.target.index
                    target_offset = block_offsets[target_block]
                    current_offset = len(instructions)
                    instruction.target = target_offset
                instructions.append(instruction)

        return instructions

@dataclass
class TypeInfo:
    fields: list[str] | None
    methods: dict[str, ast.Method]
    field_indicies: dict[str, int] | None = None
    type_index: int | None = None

class Compiler:
    def __init__(self, ast):
        self.ast = ast
        self.types = defaultdict(lambda: TypeInfo(None, {}))
        self.constants = [TraxObject(TraxObject.nil)]
        self.method_map = {}
        self.add_builtin_type('Int', 0)
        self.add_builtin_type('Bool', 2)
        self.add_builtin_type('NilType', 1)

    def compile(self):
        self.collect_types()
        self.set_fields()
        self.set_type_indexes()
        self.compile_methods()
        return self.constants, self.method_map

    def collect_types(self):
        for node in self.ast:
            if isinstance(node, ast.Struct):
                self.types[node.name].fields = [field.name for field in node.fields]
            elif isinstance(node, ast.Method):
                self.types[node.class_name].methods[node.method_name] = node

    def set_fields(self):
        for type_name, type_info in self.types.items():
            if type_info.fields is None:
                raise ValueError(f"Type '{type_name}' does not have fields set")
            type_info.field_indicies = {field: i for i, field in enumerate(type_info.fields)}

    def set_type_indexes(self):
        self.types['Int'].type_index = 0
        self.types['Bool'].type_index = 2
        self.types['NilType'].type_index = 1
        next_index = 3
        for type_name in self.types:
            if type_name not in self.types:
                self.types[type_name].type_index = next_index
                next_index += 1

    def compile_methods(self):
        for type_name, type_info in self.types.items():
            for method_name, method in type_info.methods.items():
                args, body = method.args, method.body
                mb = MethodBuilder(type_name, method_name)

                # Map arguments to indexes
                # TODO: this is no longer a stack map
                stack_map = {'self': 0}
                for i, arg in enumerate(args):
                    stack_map[arg] = i + 1

                # Compile the method body with the stack map
                self.compile_block(body, mb, stack_map)

                # Push nil before returning if no explicit return was made
                mb.push_const(TraxObject(TraxObject.nil))
                mb.return_()

                self.method_map[(type_info.type_index, method_name)] = mb.build()

    # TODO: It is slightly confusing that blocks handle variable
    #       declerations but it isn't *that* bad
    def compile_block(self, block, mb, stack_map):
        for stmt in block.stmts:
            if isinstance(stmt, ast.VarDecl):
                new_stack_map = {k: v + 1 for k, v in stack_map.items()}
                new_stack_map = dict(**stack_map)
                new_stack_map[stmt.name] = len(stack_map)
                self.compile_expr(stmt.expr, mb, stack_map)
                stack_map = new_stack_map
            else:
                self.compile_stmt(stmt, mb, stack_map)

    # TODO: The handling of self and non-self is a bit
    #       confusing here
    def compile_Assign(self, stmt: ast.Assign, mb, stack_map):
        self.compile_expr(stmt.expr, mb, stack_map)
        assert isinstance(stmt.qualified, ast.Qualified)
        if stmt.qualified.names[0] == 'self' and len(stmt.qualified.names) == 2:
            mb.get(stack_map['self'])
            self_type_info = self.types[mb.typename]
            assert self_type_info.field_indicies is not None
            mb.set_field(self_type_info.field_indicies[stmt.qualified.names[1]])
        elif len(stmt.qualified.names) == 1:
            var = stmt.qualified.names[0]
            if var in stack_map:
                mb.set(stack_map[var])
            else:
                raise ValueError(f"Unknown variable: {var}")
        else:
            raise NotImplementedError("Only self field and variable assignments are supported")

    def compile_ExprStmt(self, stmt: ast.ExprStmt, mb, stack_map):
        self.compile_expr(stmt.expr, mb, stack_map)
        mb.pop()

    def compile_stmt(self, stmt, mb, stack_map):
        method_name = f"compile_{type(stmt).__name__}"
        method = getattr(self, method_name, None)
        if method is not None:
            return method(stmt, mb, stack_map)
        else:
            raise NotImplemented(f"{type(stmt)} is not currently supported")

    def compile_If(self, stmt: ast.If, mb, stack_map):
        self.compile_expr(stmt.condition, mb, stack_map)
        end_bb = mb.new_block()
        mb.jmp_if_not(end_bb)
        self.compile_block(stmt.if_body, mb, stack_map)
        mb.jmp(end_bb)
        mb.switch_block(end_bb)

    def compile_IfElse(self, stmt: ast.IfElse, mb, stack_map):
        self.compile_expr(stmt.condition, mb, stack_map)
        else_bb = mb.new_block()
        end_bb = mb.new_block()
        mb.jmp_if_not(else_bb)
        self.compile_block(stmt.if_body, mb, stack_map)
        mb.jmp(end_bb)
        mb.switch_block(else_bb)
        self.compile_block(stmt.else_body, mb, stack_map)
        mb.jmp(end_bb)
        mb.switch_block(end_bb)

    def compile_ForLoop(self, stmt: ast.ForLoop, mb, stack_map):
        raise NotImplementedError("For loops are not yet implemented")

    def compile_WhileLoop(self, stmt: ast.WhileLoop, mb, stack_map):
        start_bb = mb.new_block()
        end_bb = mb.new_block()
        mb.jmp(start_bb)
        mb.switch_block(start_bb)
        self.compile_expr(stmt.condition, mb, stack_map)
        mb.jmp_if_not(end_bb)
        self.compile_block(stmt.body, mb, stack_map)
        mb.jmp(start_bb, loop_back=True)
        mb.switch_block(end_bb)

    def compile_Return(self, stmt: ast.Return, mb, stack_map):
        self.compile_expr(stmt.expr, mb, stack_map)
        mb.return_()

    def compile_expr(self, expr, mb, stack_map, stack_depth=0):
        method_name = f"compile_{type(expr).__name__}"
        method = getattr(self, method_name, None)
        if method is not None:
            return method(expr, mb, stack_map, stack_depth)
        else:
            raise ValueError(f"Unknown expression type: {type(expr)}")

    # TODO: This duplicates with Assign and has the same issues sort of
    def compile_Qualified(self, expr, mb, stack_map, stack_depth):
        if len(expr.names) == 1:
            obj = expr.names[0]
            if obj in stack_map:
                mb.dup(stack_depth + stack_map[obj])
            elif obj in self.constants:
                mb.push_const(self.constants.index(obj))
            else:
                raise NotImplementedError(f"Unsupported qualified expression: {obj}")
        elif len(expr.names) == 2 and expr.names[0] == 'self':
            mb.dup(stack_depth + stack_map['self'])
            self_type_info = self.types[mb.typename]
            assert self_type_info.field_indicies is not None
            mb.get_field(self_type_info.field_indicies[expr.names[1]])
        else:
            raise NotImplementedError(f"Only 'self' is allowed as the object in field access, got: {expr.names[0]}")

    def compile_MethodCall(self, expr, mb, stack_map, stack_depth):
        self.compile_expr(expr.obj, mb, stack_map, stack_depth)
        for arg in expr.args:
            self.compile_expr(arg, mb, stack_map, stack_depth + 1)
        mb.call(expr.method, len(expr.args))

    def compile_Constant(self, expr, mb, stack_map, stack_depth):
        mb.push_const(len(self.constants))
        self.constants.append(expr.value)

    def compile_NewExpr(self, expr, mb, stack_map, stack_depth):
        if expr.class_name not in self.types:
            raise ValueError(f"Unknown type: {expr.class_name}")
        type_info = self.types[expr.class_name]
        for arg in expr.args:
            self.compile_expr(arg, mb, stack_map, stack_depth)
            stack_depth += 1
        assert type_info.fields is not None
        mb.new(type_info.type_index, len(type_info.fields))

    def add_constant(self, value):
        if value not in self.constants:
            self.constants.append(value)
        return self.constants.index(value)

    def add_builtin_type(self, type_name, type_index):
        if type_name not in self.types:
            self.types[type_name] = TypeInfo([], {}, {}, type_index)
