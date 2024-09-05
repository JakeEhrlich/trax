from trax_obj import TraxObject


class TraceInstruction:
    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other

    def get_live_values(self):
        return []

    def pretty_print(self, value_to_name):
        return f"{self.__class__.__name__}"

    def copy(self, value_map):
        return self.__class__()

class GuardInstruction(TraceInstruction):
    def __init__(self, guard_id: int, operand: "ValueInstruction", values_to_keep: list["ValueInstruction"]):
        if isinstance(self, GuardNil):
            raise ValueError("why?")
        self.guard_id = guard_id
        self.operand = operand
        self.values_to_keep = values_to_keep

    def get_live_values(self):
        return [self.operand] + self.values_to_keep

    def pretty_print(self, value_to_name):
        return f"{self.__class__.__name__}(guard_id={self.guard_id}, operand={value_to_name(self.operand)}, values_to_keep=[{', '.join(value_to_name(v) for v in self.values_to_keep)}])"

    def copy(self, value_map):
        return self.__class__(self.guard_id, value_map(self.operand), [value_map(v) for v in self.values_to_keep])

    @staticmethod
    def check(args, **kwargs):
        raise NotImplementedError("Subclasses must implement this method")

class GuardNil(GuardInstruction):
    @staticmethod
    def check(args, **kwargs):
        return args[0].is_nil()

class GuardInt(GuardInstruction):
    @staticmethod
    def check(args, **kwargs):
        return args[0].is_integer()

class GuardBool(GuardInstruction):
    @staticmethod
    def check(args, **kwargs):
        return args[0].is_boolean()

class GuardTrue(GuardInstruction):
    @staticmethod
    def check(args, **kwargs):
        return args[0].is_true()

class GuardIndex(GuardInstruction):
    def __init__(self, guard_id: int, operand: "ValueInstruction", values_to_keep: list["ValueInstruction"], *, type_index: int,):
        super().__init__(guard_id, operand, values_to_keep)
        self.type_index = type_index

    def pretty_print(self, value_to_name):
        return f"{self.__class__.__name__}(guard_id={self.guard_id}, operand={value_to_name(self.operand)}, type_index={self.type_index}, values_to_keep=[{', '.join(value_to_name(v) for v in self.values_to_keep)}])"

    def copy(self, value_map):
        return self.__class__(self.guard_id, value_map(self.operand), [value_map(v) for v in self.values_to_keep], type_index=self.type_index)

    @staticmethod
    def check(args, **kwargs):
        return args[0].is_object() and args[0].get_type_index() == kwargs["type_index"]

class GuardCond(GuardInstruction):
    def __init__(self, guard_id: int, operand: "ValueInstruction", right: "ValueInstruction", values_to_keep: list["ValueInstruction"]):
        super().__init__(guard_id, operand, values_to_keep)
        self.right = right

    def get_live_values(self):
        return [self.operand, self.right] + self.values_to_keep

    def pretty_print(self, value_to_name):
        return f"{self.__class__.__name__}(guard_id={self.guard_id}, operand={value_to_name(self.operand)}, right={value_to_name(self.right)}, values_to_keep=[{', '.join(value_to_name(v) for v in self.values_to_keep)}])"

    def copy(self, value_map):
        return self.__class__(self.guard_id, value_map(self.operand), value_map(self.right), [value_map(v) for v in self.values_to_keep])

class GuardLT(GuardCond):
    @staticmethod
    def check(args, **kwargs):
        return args[0].to_int() < args[1].to_int()

class GuardLE(GuardCond):
    @staticmethod
    def check(args, **kwargs):
        return args[0].to_int() <= args[1].to_int()

class GuardGT(GuardCond):
    @staticmethod
    def check(args, **kwargs):
        return args[0].to_int() > args[1].to_int()

class GuardGE(GuardCond):
    @staticmethod
    def check(args, **kwargs):
        return args[0].to_int() >= args[1].to_int()

class GuardEQ(GuardCond):
    @staticmethod
    def check(args, **kwargs):
        return args[0].to_int() == args[1].to_int()

class GuardNE(GuardCond):
    @staticmethod
    def check(args, **kwargs):
        return args[0].to_int() != args[1].to_int()

class ValueInstruction(TraceInstruction):
    def pretty_print(self, value_to_name):
        return f"{value_to_name(self)} = {self.__class__.__name__}"

    def copy(self, value_map):
        return self.__class__()

    def interp(self, args):
        raise NotImplementedError("Subclasses must implement this method")

class ConstantInstruction(ValueInstruction):
    def __init__(self, object: TraxObject):
        self.object = object
        self.type_index = object.get_type_index()

    def get_live_values(self):
        return []

    def pretty_print(self, value_to_name):
        return f"{value_to_name(self)} = {self.__class__.__name__}(constant_index={self.constant_index})"

    def copy(self, value_map):
        return self.__class__(self.object)

    def interp(self, args):
        return self.object

class BinaryOpInstruction(ValueInstruction):
    def __init__(self, left, right, type_index):
        self.left = left
        self.right = right
        self.type_index = type_index

    def get_live_values(self):
        return [self.left, self.right]

    def pretty_print(self, value_to_name):
        return f"{value_to_name(self)} = {self.__class__.__name__}({value_to_name(self.left)}, {value_to_name(self.right)})"

    def copy(self, value_map):
        return self.__class__(value_map(self.left), value_map(self.right), self.type_index)

class UnaryOpInstruction(ValueInstruction):
    def __init__(self, operand, type_index):
        self.operand = operand
        self.type_index = type_index

    def get_live_values(self):
        return [self.operand]

    def pretty_print(self, value_to_name):
        return f"{value_to_name(self)} = {self.__class__.__name__}({value_to_name(self.operand)})"

    def copy(self, value_map):
        return self.__class__(value_map(self.operand), self.type_index)

class BoolBinInstruction(BinaryOpInstruction):
    def __init__(self, left, right):
        self.left = left
        self.right = right
        self.type_index = 2

    def copy(self, value_map):
        return self.__class__(value_map(self.left), value_map(self.right))

class BoolUnaryInstruction(UnaryOpInstruction):
    def __init__(self, operand):
        self.operand = operand
        self.type_index = 2

    def copy(self, value_map):
        return self.__class__(value_map(self.operand))

class EqInstruction(BoolBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_bool(left.value.value == right.value.value)

class NeInstruction(BoolBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_bool(left.value.value != right.value.value)

class LtInstruction(BoolBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_bool(left.to_int() < right.to_int())

class GtInstruction(BoolBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_bool(left.to_int() > right.to_int())

class LeInstruction(BoolBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_bool(left.to_int() <= right.to_int())

class GeInstruction(BoolBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_bool(left.to_int() >= right.to_int())

class LogicalOrInstruction(BoolBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_bool(left.to_bool() or right.to_bool())

class LogicalAndInstruction(BoolBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_bool(left.to_bool() and right.to_bool())

class LogicalNotInstruction(BoolUnaryInstruction):
    def interp(self, args):
        operand = self.operand.interp(args)
        return operand.from_bool(not operand.to_bool())

class IntToBoolInstruction(BoolUnaryInstruction):
    def interp(self, args):
        operand = self.operand.interp(args)
        return operand.from_bool(bool(operand.to_int()))

class IntBinInstruction(BinaryOpInstruction):
    def __init__(self, left, right):
        self.left = left
        self.right = right
        self.type_index = 0

    def copy(self, value_map):
        return self.__class__(value_map(self.left), value_map(self.right))

class IntUnaryInstruction(UnaryOpInstruction):
    def __init__(self, operand):
        self.operand = operand
        self.type_index = 0

    def copy(self, value_map):
        return self.__class__(value_map(self.operand))

class AddInstruction(IntBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_int(left.to_int() + right.to_int())

class SubInstruction(IntBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_int(left.to_int() - right.to_int())

class MulInstruction(IntBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_int(left.to_int() * right.to_int())

class DivInstruction(IntBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_int(left.to_int() // right.to_int())

class ModInstruction(IntBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_int(left.to_int() % right.to_int())

class MaxInstruction(IntBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_int(max(left.to_int(), right.to_int()))

class MinInstruction(IntBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_int(min(left.to_int(), right.to_int()))

class BwAndInstruction(IntBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_int(left.to_int() & right.to_int())

class BwOrInstruction(IntBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_int(left.to_int() | right.to_int())

class BwXorInstruction(IntBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_int(left.to_int() ^ right.to_int())

class LslInstruction(IntBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_int(left.to_int() << right.to_int())

class LsrInstruction(IntBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_int(left.to_int() >> right.to_int())

class AsrInstruction(IntBinInstruction):
    def interp(self, args):
        left = self.left.interp(args)
        right = self.right.interp(args)
        return left.from_int(left.to_int() >> right.to_int())

class BwNotInstruction(IntUnaryInstruction):
    def interp(self, args):
        operand = self.operand.interp(args)
        return operand.from_int(~operand.to_int())

class BoolToIntInstruction(IntUnaryInstruction):
    def interp(self, args):
        operand = self.operand.interp(args)
        return operand.from_int(1 if operand.to_bool() else 0)

class GetVar(ValueInstruction):
    frame_idx: int
    var_idx: int

    def __init__(self, frame_idx, var_idx):
        self.frame_idx = frame_idx
        self.var_idx = var_idx

    def get_live_values(self):
        return []

    def pretty_print(self, value_to_name):
        return f"{value_to_name(self)} = {self.__class__.__name__}(frame_idx={self.frame_idx}, var_idx={self.var_idx})"

    def copy(self, value_map):
        return GetVar(self.frame_idx, self.var_idx)

class SetVar(TraceInstruction):
    frame_idx: int
    var_idx: int
    value: ValueInstruction

    def __init__(self, frame_idx, var_idx, value):
        self.frame_idx = frame_idx
        self.var_idx = var_idx
        self.value = value

    def get_live_values(self):
        return [self.value]

    def pretty_print(self, value_to_name):
        return f"{self.__class__.__name__}(frame_idx={self.frame_idx}, var_idx={self.var_idx}, value={value_to_name(self.value)})"

    def copy(self, value_map):
        return SetVar(self.frame_idx, self.var_idx, value_map(self.value))

# class InputInstruction(ValueInstruction):
#     phi: ValueInstruction
#     input_index: int

#     def __init__(self, input_index):
#         self.input_index = input_index
#         self.phi = self

#     def get_live_values(self):
#         return []

#     def pretty_print(self, value_to_name):
#         return f"{value_to_name(self)} = {self.__class__.__name__}(input_index={self.input_index})"

#     def copy(self, value_map):
#         raise ValueError("You cannot copy an input instruction")

class GetFieldInstruction(ValueInstruction):
    def __init__(self, obj, field_index):
        self.obj = obj
        self.field_index = field_index

    def get_live_values(self):
        return [self.obj]

    def pretty_print(self, value_to_name):
        return f"{value_to_name(self)} = {self.__class__.__name__}({value_to_name(self.obj)}, field_index={self.field_index})"

    def copy(self, value_map):
        return self.__class__(value_map(self.obj), self.field_index)

class SetFieldInstruction(TraceInstruction):
    def __init__(self, obj, field_index, value):
        self.obj = obj
        self.field_index = field_index
        self.value = value

    def get_live_values(self):
        return [self.obj, self.value]

    def pretty_print(self, value_to_name):
        return f"{self.__class__.__name__}({value_to_name(self.obj)}, field_index={self.field_index}, value={value_to_name(self.value)})"

    def copy(self, value_map):
        return self.__class__(value_map(self.obj), self.field_index, value_map(self.value))

class NewInstruction(ValueInstruction):
    def __init__(self, type_index, num_fields):
        self.type_index = type_index
        self.num_fields = num_fields

    def get_live_values(self):
        return []

    def pretty_print(self, value_to_name):
        return f"{value_to_name(self)} = {self.__class__.__name__}(type_index={self.type_index}, num_fields={self.num_fields})"

    def copy(self, value_map):
        return self.__class__(self.type_index, self.num_fields)

# Copy instructions are for creating copies from the preamble to the body which may sometimes be needed
# class CopyInstruction(TraceInstruction):
#     input: InputInstruction
#     value: ValueInstruction

#     def __init__(self, input, value):
#         self.input = input
#         self.value = value

#     def get_live_values(self):
#         return [self.value, self.input]

#     def pretty_print(self, value_to_name):
#         return f"{self.__class__.__name__}(input={value_to_name(self.value)}, value={value_to_name(self.value)})"

#     def copy(self, value_map):
#         raise ValueError("You cannot copy a copy instruction")

class TraceCompiler:
    def __init__(self):
        self.instructions = []

    def add_instruction(self, instruction):
        self.instructions.append(instruction)

    def guard_nil(self, guard_id, operand, values_to_keep):
        self.add_instruction(GuardNil(guard_id, operand, values_to_keep))

    def guard_int(self, guard_id, operand, values_to_keep):
        self.add_instruction(GuardInt(guard_id, operand, values_to_keep))

    def guard_bool(self, guard_id, operand, values_to_keep):
        self.add_instruction(GuardBool(guard_id, operand, values_to_keep))

    def guard_true(self, guard_id, operand, values_to_keep):
        self.add_instruction(GuardTrue(guard_id, operand, values_to_keep))

    def guard_index(self, guard_id, operand, type_index, values_to_keep):
        self.add_instruction(GuardIndex(guard_id, operand, type_index, values_to_keep))

    def constant(self, constant_index, type_index):
         instruction = ConstantInstruction(constant_index, type_index)
         self.add_instruction(instruction)
         return instruction

    def input(self, input_index):
        instruction = InputInstruction(input_index)
        self.add_instruction(instruction)
        return instruction

    def add(self, left, right):
        instruction = AddInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def sub(self, left, right):
        instruction = SubInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def mul(self, left, right):
        instruction = MulInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def div(self, left, right):
        instruction = DivInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def mod(self, left, right):
        instruction = ModInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def eq(self, left, right):
        instruction = EqInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def ne(self, left, right):
        instruction = NeInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def lt(self, left, right):
        instruction = LtInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def gt(self, left, right):
        instruction = GtInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def le(self, left, right):
        instruction = LeInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def ge(self, left, right):
        instruction = GeInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def logical_and(self, left, right):
        instruction = LogicalAndInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def logical_or(self, left, right):
        instruction = LogicalOrInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def logical_not(self, operand):
        instruction = LogicalNotInstruction(operand)
        self.add_instruction(instruction)
        return instruction

    def bw_and(self, left, right):
        instruction = BwAndInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def bw_or(self, left, right):
        instruction = BwOrInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def bw_xor(self, left, right):
        instruction = BwXorInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def bw_not(self, operand):
        instruction = BwNotInstruction(operand)
        self.add_instruction(instruction)
        return instruction

    def lsl(self, left, right):
        instruction = LslInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def lsr(self, left, right):
        instruction = LsrInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def asr(self, left, right):
        instruction = AsrInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def max(self, left, right):
        instruction = MaxInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def min(self, left, right):
        instruction = MinInstruction(left, right)
        self.add_instruction(instruction)
        return instruction

    def bool_to_int(self, operand):
        instruction = BoolToIntInstruction(operand)
        self.add_instruction(instruction)
        return instruction

    def int_to_bool(self, operand):
        instruction = IntToBoolInstruction(operand)
        self.add_instruction(instruction)
        return instruction

    def get_field(self, obj, field_index):
        instruction = GetFieldInstruction(obj, field_index)
        self.add_instruction(instruction)
        return instruction

    def set_field(self, obj, field_index, value):
        instruction = SetFieldInstruction(obj, field_index, value)
        self.add_instruction(instruction)
        return instruction

    def new(self, type_index, num_fields):
        instruction = NewInstruction(type_index, num_fields)
        self.add_instruction(instruction)
        return instruction

    def get_instructions(self):
        return list(self.instructions)

    def optimize(self):
        self.remove_redundant_guards() # Guards get repeated a lot, remove repeated ones
        self.dead_value_elimination(get_liveness_ranges(self.instructions)) # Don't need to compute dead values
        self.optimize_constant_guards() # Sometimes we guard on a constants
        self.remove_trivial_guards() # Sometimes we guard on something we know the type of
        self.optimize_guards(get_liveness_ranges(self.instructions)) # Sometimes there's a better guard we can use
        self.unroll_and_lift()

    # This is a somewhat tracing jit specific optimization, we want to recognize that the initital inputs
    # might not be of a fixed class but after that we might know with certainy that they are. This leads
    # us to the strategy of running once with all guards, then running again where we might know the type
    # an input
    def unroll_and_lift(self):
        self.preamble = list(self.instructions)
        self.body = []
        preamble_to_body = {}
        value_types = {}

        # Now we get type info that will be valid at the *start* of the next iteration
        for inst in self.instructions:
            for instruction in self.instructions:
                if isinstance(instruction, GuardInt):
                    if instruction.operand in value_types and value_types[instruction.operand] == 0:
                        continue
                    value_types[instruction.operand] = 0

                if isinstance(instruction, GuardTrue):
                    if instruction.operand in value_types and value_types[instruction.operand] == 2:
                        continue
                    value_types[instruction.operand] = 2

                if isinstance(instruction, GuardNil):
                    if instruction.operand in value_types and value_types[instruction.operand] == 1:
                        continue
                    value_types[instruction.operand] = 1

                if isinstance(instruction, BinaryOpInstruction):
                    value_types[instruction] = instruction.type_index

        # Now we emit the body instructions
        phi_nodes = {}
        for instruction in self.instructions:
            if isinstance(instruction, InputInstruction):
                preamble_to_body[instruction] = instruction
                # We know the type of this in the second run
                if instruction is not instruction.phi:
                    value_types[instruction] = value_types[instruction.phi]
                    phi_nodes[instruction.phi] = instruction # We need know about phi nodes later so that we can update them
                self.preamble.append(CopyInstruction(instruction, instruction.phi))
                continue

            # This hurts register pressure but seems like an ok idea for now
            # This code makes it so that constants from the preamble are reused in the inner loop
            if isinstance(instruction, ConstantInstruction):
                preamble_to_body[instruction] = instruction
                continue

            if isinstance(instruction, GuardInt):
                if instruction.operand in value_types and value_types[instruction.operand] == 0:
                    continue
                value_types[instruction.operand] = 0

            if isinstance(instruction, GuardTrue):
                if instruction.operand in value_types and value_types[instruction.operand] == 2:
                    continue
                value_types[instruction.operand] = 2

            if isinstance(instruction, GuardNil):
                if instruction.operand in value_types and value_types[instruction.operand] == 1:
                    continue
                value_types[instruction.operand] = 1

            if isinstance(instruction, BinaryOpInstruction):
                value_types[instruction] = instruction.type_index

            new_inst = instruction.copy(lambda v: preamble_to_body[v])
            if instruction in phi_nodes:
                phi_nodes[instruction].phi = new_inst # remap phi nodes
            preamble_to_body[instruction] = new_inst
            self.body.append(new_inst)

    def optimize_guards(self, liveness_ranges):
        optimized_instructions = []
        skip_next = False
        for i, instruction in enumerate(self.instructions):
            if skip_next:
                skip_next = False
                continue

            if isinstance(instruction, BoolBinInstruction) and i + 1 < len(self.instructions):
                next_instruction = self.instructions[i + 1]
                if isinstance(next_instruction, GuardTrue) and next_instruction.operand is instruction:
                    # Check if the BoolBinInstruction result is no longer used
                    is_unused = liveness_ranges[instruction][1] <= i + 1

                    if is_unused:
                        if isinstance(instruction, EqInstruction):
                            optimized_instructions.append(GuardEQ(next_instruction.guard_id, instruction.left, instruction.right, next_instruction.values_to_keep))
                        elif isinstance(instruction, NeInstruction):
                            optimized_instructions.append(GuardNE(next_instruction.guard_id, instruction.left, instruction.right, next_instruction.values_to_keep))
                        elif isinstance(instruction, LtInstruction):
                            optimized_instructions.append(GuardLT(next_instruction.guard_id, instruction.left, instruction.right, next_instruction.values_to_keep))
                        elif isinstance(instruction, GtInstruction):
                            optimized_instructions.append(GuardGT(next_instruction.guard_id, instruction.left, instruction.right, next_instruction.values_to_keep))
                        elif isinstance(instruction, LeInstruction):
                            optimized_instructions.append(GuardLE(next_instruction.guard_id, instruction.left, instruction.right, next_instruction.values_to_keep))
                        elif isinstance(instruction, GeInstruction):
                            optimized_instructions.append(GuardGE(next_instruction.guard_id, instruction.left, instruction.right, next_instruction.values_to_keep))
                        skip_next = True
                        continue

            optimized_instructions.append(instruction)

        self.instructions = optimized_instructions

    # This goes through and just keeps track of trivial type info and uses
    # it to remove some guards
    def remove_trivial_guards(self):
        from collections import defaultdict
        value_types = {}
        change = True
        new_instructions = []

        for instruction in self.instructions:
            if isinstance(instruction, GuardInt):
                if instruction.operand in value_types and value_types[instruction.operand] == 0:
                    continue
                value_types[instruction.operand] = 0

            if isinstance(instruction, GuardTrue):
                if instruction.operand in value_types and value_types[instruction.operand] == 2:
                    continue
                value_types[instruction.operand] = 2

            if isinstance(instruction, GuardNil):
                if instruction.operand in value_types and value_types[instruction.operand] == 1:
                    continue
                value_types[instruction.operand] = 1

            if isinstance(instruction, BinaryOpInstruction):
                value_types[instruction] = instruction.type_index

            new_instructions.append(instruction)

    def dead_value_elimination(self, liveness_ranges):
        used = set()
        for instruction in self.instructions:
            if isinstance(instruction, ValueInstruction):
                (start, end) = liveness_ranges[instruction]
                if start != end:
                    used.add(instruction)
            else:
                used.add(instruction)

        optimized_instructions = [
            inst for inst in self.instructions
            if inst in used
        ]

        self.instructions = optimized_instructions

    def optimize_constant_guards(self):
        optimized_instructions = []
        for instruction in self.instructions:
            if isinstance(instruction, GuardInstruction) and isinstance(instruction.operand, ConstantInstruction):
                constant = instruction.operand.object
                if isinstance(instruction, GuardNil) and constant.is_nil():
                    continue  # Remove the guard as it's sure to succeed
                elif isinstance(instruction, GuardInt) and constant.is_integer():
                    continue  # Remove the guard as it's sure to succeed
                elif isinstance(instruction, GuardBool) and constant.is_boolean():
                    continue  # Remove the guard as it's sure to succeed
                elif isinstance(instruction, GuardTrue) and constant.is_true():
                    continue  # Remove the guard as it's sure to succeed
                elif isinstance(instruction, GuardIndex) and constant.is_object() and constant.get_type_index() == instruction.type_index:
                    continue  # Remove the guard as it's sure to succeed
                else:
                    print(f"Warning: Guard {instruction.__class__.__name__} on constant {constant} is sure to fail")
            optimized_instructions.append(instruction)
        self.instructions = optimized_instructions

    def remove_redundant_guards(self):
        guarded_values = {}
        optimized_instructions = []

        for instruction in self.instructions:
            if isinstance(instruction, GuardInstruction):
                key = (type(instruction), instruction.operand)
                if key not in guarded_values:
                    guarded_values[key] = instruction.guard_id
                    optimized_instructions.append(instruction)
            else:
                optimized_instructions.append(instruction)

        self.instructions = optimized_instructions

    def pretty_print(self):
        value_to_name = {}
        name_counter = 0

        def get_value_name(value):
            if value not in value_to_name:
                nonlocal name_counter
                value_to_name[value] = f"v{name_counter}"
                name_counter += 1
            return value_to_name[value]

        pretty_instructions = []
        if self.preamble is not None:
            pretty_instructions.append("pre:")
            for instruction in self.preamble:
                pretty_instructions.append("  " + instruction.pretty_print(get_value_name))
            pretty_instructions.append("post:")
            for instruction in self.body:
                pretty_instructions.append("  " + instruction.pretty_print(get_value_name))
        else:
            for instruction in self.instructions:
                pretty_instructions.append(instruction.pretty_print(get_value_name))

        return "\n".join(pretty_instructions)

def get_liveness_ranges(instructions):
    liveness = {}
    phi_nodes = {}

    def update_liveness(value, idx):
        start, end = liveness[value]
        liveness[value] = (start, max(end, idx))

    for idx, inst in enumerate(instructions):
        # Because there are no cycles and only ValueInstructions can
        # be operands, this is the first time we will have seen this value
        if isinstance(inst, ValueInstruction):
            liveness[inst] = (idx, idx)

        # We'll use this later to tie the knot if possible
        if isinstance(inst, InputInstruction) and inst.phi is not None:
            phi_nodes[inst.phi] = inst

        # phi_nodes never die
        if inst in phi_nodes:
            liveness[inst] = (idx, len(instructions))

        # Now we can just find all operands and update the max on them
        for value in inst.get_live_values():
            update_liveness(value, idx)

    return liveness

def allocate_registers(instructions, available_registers):
    liveness_ranges = get_liveness_ranges(instructions)
    register_allocation = {}
    used_registers = set()
    phi_nodes = {}

    for idx, inst in enumerate(instructions):
        for value in inst.get_live_values():
            if liveness_ranges[value][1] == idx:
                reg = register_allocation[value]
                if reg in used_registers:
                    used_registers.remove(reg)

        # We'll use this later to tie the knot if possible
        if isinstance(inst, InputInstruction) and inst.phi is not None:
            phi_nodes[inst.phi] = inst

        if isinstance(inst, ValueInstruction):
            # If this is a phi node, try our best to tie the knot.
            # If an input is its own phi node, there's nothing special we need to do
            # if inst in phi_nodes and phi_nodes[inst] is not inst:
            #     if register_allocation[phi_nodes[inst]] not in used_registers:
            #         reg = register_allocation[phi_nodes[inst]]
            #         register_allocation[inst] = reg
            #         used_registers.add(reg)
            #         continue

            # Find the first available register
            for reg in available_registers:
                if reg not in used_registers:
                    register_allocation[inst] = reg
                    used_registers.add(reg)
                    break
            else:
                # TODO: Implement spilling
                raise ValueError("Not enough registers for allocation")
    return register_allocation
