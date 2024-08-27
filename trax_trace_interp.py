from trax_tracing import *
from trax_obj import *

class GuardException(Exception):
    def __init__(self, guard_instruction, value_map):
        self.guard_instruction = guard_instruction
        self.value_map = value_map
        super().__init__(f"Guard failed: {guard_instruction}")

class TraceInterpreter:
    def __init__(self, constant_table):
        self.constant_table = constant_table

    def interpret(self, instructions, inputs, return_value):
        value_map = {}

        for inst in instructions:
            if isinstance(inst, InputInstruction):
                value_map[inst] = inputs[inst.input_index]
            elif isinstance(inst, ConstantInstruction):
                value_map[inst] = self.constant_table[inst.constant_index]
            elif isinstance(inst, AddInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_int(left + right)
            elif isinstance(inst, SubInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_int(left - right)
            elif isinstance(inst, MulInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_int(left * right)
            elif isinstance(inst, DivInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_int(left // right)
            elif isinstance(inst, ModInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_int(left % right)
            elif isinstance(inst, EqInstruction):
                left = value_map[inst.left]
                right = value_map[inst.right]
                value_map[inst] = TraxObject.from_bool(left.value == right.value)
            elif isinstance(inst, NeInstruction):
                left = value_map[inst.left]
                right = value_map[inst.right]
                value_map[inst] = TraxObject.from_bool(left.value != right.value)
            elif isinstance(inst, LtInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_bool(left < right)
            elif isinstance(inst, GtInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_bool(left > right)
            elif isinstance(inst, LeInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_bool(left <= right)
            elif isinstance(inst, GeInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_bool(left >= right)
            elif isinstance(inst, MaxInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_int(max(left, right))
            elif isinstance(inst, MinInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_int(min(left, right))
            elif isinstance(inst, BwAndInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_int(left & right)
            elif isinstance(inst, BwOrInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_int(left | right)
            elif isinstance(inst, BwXorInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_int(left ^ right)
            elif isinstance(inst, LslInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_int(left << right)
            elif isinstance(inst, LsrInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_int(left >> right)
            elif isinstance(inst, AsrInstruction):
                left = value_map[inst.left].to_int()
                right = value_map[inst.right].to_int()
                value_map[inst] = TraxObject.from_int(left >> right)
            elif isinstance(inst, BoolToIntInstruction):
                operand = value_map[inst.operand]
                value_map[inst] = TraxObject.from_int(1 if operand.is_true() else 0)
            elif isinstance(inst, IntToBoolInstruction):
                operand = value_map[inst.operand].to_int()
                value_map[inst] = TraxObject.from_bool(bool(operand))
            elif isinstance(inst, GetFieldInstruction):
                obj = value_map[inst.obj]
                value_map[inst] = obj.get_field(inst.field_index)
            elif isinstance(inst, SetFieldInstruction):
                obj = value_map[inst.obj]
                value = value_map[inst.value]
                obj.set_field(inst.field_index, value)
            #elif isinstance(inst, NewInstruction):
            #    value_map[inst] = TraxObject.new(inst.type_index, [])
            elif isinstance(inst, GuardInstruction):
                operand = value_map[inst.operand]
                if isinstance(inst, GuardNil) and not operand.is_nil():
                    raise GuardException(inst, value_map)
                elif isinstance(inst, GuardInt) and not operand.is_integer():
                    raise GuardException(inst, value_map)
                elif isinstance(inst, GuardBool) and not operand.is_boolean():
                    raise GuardException(inst, value_map)
                elif isinstance(inst, GuardTrue) and not operand.is_true():
                    raise GuardException(inst, value_map)
                elif isinstance(inst, GuardIndex) and (not operand.is_object() or operand.get_type_index() != inst.type_index):
                    raise GuardException(inst, value_map)
            else:
                raise ValueError(f"Trace interpreter not implemented instruction: type: {type(inst)}")

        return value_map[return_value]
