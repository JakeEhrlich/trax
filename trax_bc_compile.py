from trax_ast import *
from trax_obj import TraxObject

class BB:
    def __init__(self, index):
        self.index = index

class MethodBuilder:
    def __init__(self, typename, method_name):
        self.typename = typename
        self.method_name = method_name
        self.blocks = []
        self.new_block()
        self.current_block = self.blocks[0]

    def new_block(self):
        block = {'instructions': []}
        self.blocks.append(block)
        return BB(len(self.blocks) - 1)

    def switch_block(self, bb):
        if 0 <= bb.index < len(self.blocks):
            self.current_block = self.blocks[bb.index]
        else:
            raise ValueError(f"Invalid block index: {bb.index}")

    def get_current_block(self):
        return self.current_block

    def add_instruction(self, opcode, **kwargs):
        instruction = {'opcode': opcode, **kwargs}
        self.current_block['instructions'].append(instruction)

    def push_const(self, const_index):
        self.add_instruction('push_const', const_index=const_index)

    def dup(self, k):
        self.add_instruction('dup', k=k)

    def pop(self):
        self.add_instruction('pop')

    def set(self, k):
        self.add_instruction('set', k=k)

    def call(self, method_name, num_args):
        self.add_instruction('call', method_name=method_name, num_args=num_args)

    def jmp(self, bb, loop_back=False):
        self.add_instruction('jmp', target=bb.index, loop_back=loop_back)

    def jmp_if_not(self, bb):
        self.add_instruction('jmp_if_not', target=bb.index)

    def get_field(self, field_index):
        self.add_instruction('get_field', field_index=field_index)

    def set_field(self, field_index):
        self.add_instruction('set_field', field_index=field_index)

    def new(self, type_index, num_fields):
        self.add_instruction('new', type_index=type_index, num_fields=num_fields)

    def return_(self, num_args=1):
        self.add_instruction('return', num_args=num_args)

    def build(self):
        # First pass: calculate offsets for each block
        block_offsets = {}
        offset = 0
        for i, block in enumerate(self.blocks):
            block_offsets[i] = offset
            offset += len(block['instructions'])

        # Second pass: build instructions and resolve jumps
        instructions = []
        for i, block in enumerate(self.blocks):
            for instruction in block['instructions']:
                instruction = dict(**instruction)
                if instruction['opcode'] in ('jmp', 'jmp_if_not'):
                    target_block = instruction['target']
                    target_offset = block_offsets[target_block]
                    current_offset = len(instructions)
                    instruction['offset'] = target_offset - current_offset - 1
                    del instruction['target']
                instructions.append(instruction)

        return instructions

class Compiler:
    def __init__(self, ast):
        self.ast = ast
        self.types = {}
        self.constants = [TraxObject(TraxObject.nil)]
        self.method_map = {}
        self.add_builtin_type('Int')
        self.add_builtin_type('Bool')
        self.add_builtin_type('NilType')

    def compile(self):
        self.collect_types()
        self.set_fields()
        self.set_type_indexes()
        self.compile_methods()
        return self.constants, self.method_map

    def collect_types(self):
        for node in self.ast:
            if isinstance(node, Struct):
                if node.name not in self.types:
                    self.types[node.name] = {'fields': None, 'methods': {}}
                self.types[node.name]['fields'] = [field.name for field in node.fields]
            elif isinstance(node, Method):
                if node.class_name not in self.types:
                    self.types[node.class_name] = {'fields': None, 'methods': {}}
                self.types[node.class_name]['methods'][node.method_name] = (node.args, node.body)

    def set_fields(self):
        for type_name, type_info in self.types.items():
            if type_info['fields'] is None:
                raise ValueError(f"Type '{type_name}' does not have fields set")
            type_info['field_indices'] = {field: i for i, field in enumerate(type_info['fields'])}

    def set_type_indexes(self):
        self.types['Int']['type_index'] = 0
        self.types['Bool']['type_index'] = 1
        self.types['NilType']['type_index'] = 2
        next_index = 3
        for type_name in self.types:
            if type_name not in ('Int', 'Bool', 'NilType'):
                self.types[type_name]['type_index'] = next_index
                next_index += 1

    def compile_methods(self):
        for type_name, type_info in self.types.items():
            for method_name, (args, body) in type_info['methods'].items():
                print(method_name, args)
                mb = MethodBuilder(type_name, method_name)

                # Map arguments to stack indices
                stack_map = {'self': len(args)}
                for i, arg in enumerate(reversed(args)):
                    stack_map[arg] = i
                print("stack_map: ", stack_map)
                # Compile the method body with the stack map
                self.compile_block(body, mb, stack_map, len(args) + 1)

                # Push nil before returning if no explicit return was made
                mb.push_const(0)
                mb.return_(len(args) + 1)

                self.method_map[(type_info['type_index'], method_name)] = mb.build()

    def compile_block(self, block, mb, stack_map, arg_count):
        for stmt in block.stmts:
            if isinstance(stmt, VarDecl):
                new_stack_map = {k: v + 1 for k, v in stack_map.items()}
                self.compile_expr(stmt.expr, mb, stack_map)
                new_stack_map[stmt.name] = 0
                stack_map = new_stack_map
            else:
                self.compile_stmt(stmt, mb, stack_map, arg_count)

    def compile_stmt(self, stmt, mb, stack_map, arg_count):
        if isinstance(stmt, Assign):
            self.compile_expr(stmt.expr, mb, stack_map)
            if isinstance(stmt.qualified, Qualified):
                if stmt.qualified.names[0] == 'self' and len(stmt.qualified.names) == 2:
                    mb.dup(stack_map['self'] + 1)
                    mb.set_field(self.types[mb.typename]['field_indices'][stmt.qualified.names[1]])
                elif len(stmt.qualified.names) == 1:
                    var = stmt.qualified.names[0]
                    if var in stack_map:
                        mb.set(stack_map[var] + 1)
                    else:
                        raise ValueError(f"Unknown variable: {var}")
                else:
                    raise NotImplementedError("Only self field and variable assignments are supported")
        elif isinstance(stmt, ExprStmt):
            self.compile_expr(stmt.expr, mb, stack_map)
            mb.pop()
        elif isinstance(stmt, If):
            self.compile_expr(stmt.condition, mb, stack_map)
            end_bb = mb.new_block()
            mb.jmp_if_not(end_bb)
            self.compile_block(stmt.if_body, mb, stack_map, arg_count)
            mb.jmp(end_bb)
            mb.switch_block(end_bb)
        elif isinstance(stmt, IfElse):
            self.compile_expr(stmt.condition, mb, stack_map)
            else_bb = mb.new_block()
            end_bb = mb.new_block()
            mb.jmp_if_not(else_bb)
            self.compile_block(stmt.if_body, mb, stack_map, arg_count)
            mb.jmp(end_bb)
            mb.switch_block(else_bb)
            self.compile_block(stmt.else_body, mb, stack_map, arg_count)
            mb.jmp(end_bb)
            mb.switch_block(end_bb)
        elif isinstance(stmt, ForLoop):
            raise NotImplementedError("For loops are not yet implemented")
        elif isinstance(stmt, WhileLoop):
            start_bb = mb.new_block()
            end_bb = mb.new_block()
            mb.jmp(start_bb)
            mb.switch_block(start_bb)
            self.compile_expr(stmt.condition, mb, stack_map)
            mb.jmp_if_not(end_bb)
            self.compile_block(stmt.body, mb, stack_map, arg_count)
            mb.jmp(start_bb, loop_back=True)
            mb.switch_block(end_bb)
        elif isinstance(stmt, VarDecl):
            raise NotImplementedError("Variable declarations are not yet implemented")
        elif isinstance(stmt, Return):
            self.compile_expr(stmt.expr, mb, stack_map)
            mb.return_(arg_count)
        else:
            raise ValueError(f"Unknown statement type: {type(stmt)}")

    def compile_expr(self, expr, mb, stack_map, stack_depth=0):
        if isinstance(expr, Qualified):
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
                mb.get_field(self.types[mb.typename]['field_indices'][expr.names[1]])
            else:
                raise NotImplementedError(f"Only 'self' is allowed as the object in field access, got: {expr.names[0]}")
        elif isinstance(expr, MethodCall):
            self.compile_expr(expr.obj, mb, stack_map, stack_depth)
            for arg in expr.args:
                self.compile_expr(arg, mb, stack_map, stack_depth + 1)
            mb.call(expr.method, len(expr.args))
        elif isinstance(expr, Constant):
            mb.push_const(len(self.constants))
            self.constants.append(expr.value)
        elif isinstance(expr, NewExpr):
            if expr.class_name not in self.types:
                raise ValueError(f"Unknown type: {expr.class_name}")
            type_info = self.types[expr.class_name]
            for arg in expr.args:
                self.compile_expr(arg, mb, stack_map, stack_depth)
                stack_depth += 1
            mb.new(type_info['type_index'], len(type_info['fields']))
        else:
            raise ValueError(f"Unknown expression type: {type(expr)}")

    def add_constant(self, value):
        if value not in self.constants:
            self.constants.append(value)
        return self.constants.index(value)

    def add_builtin_type(self, type_name):
        if type_name not in self.types:
            self.types[type_name] = {'fields': [], 'methods': {}, 'field_indices': {}}
