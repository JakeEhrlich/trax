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
            value_map[inst] = inst.interp(inputs, self.constant_table)
            if isinstance(inst, GuardInstruction):
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

        return value_map[return_value]
