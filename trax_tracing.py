class TraceInstruction:
    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other

    def get_live_values(self):
        return []

    def pretty_print(self, value_to_name):
        return f"{self.__class__.__name__}"

class GuardInstruction(TraceInstruction):
    def __init__(self, guard_id: int, operand: "ValueInstruction", values_to_keep: list["ValueInstruction"]):
        self.guard_id = guard_id
        self.operand = operand
        self.values_to_keep = values_to_keep

    def get_live_values(self):
        return [self.operand] + self.values_to_keep

    def pretty_print(self, value_to_name):
        return f"{self.__class__.__name__}(guard_id={self.guard_id}, operand={value_to_name(self.operand)}, values_to_keep=[{', '.join(value_to_name(v) for v in self.values_to_keep)}])"

class GuardNil(GuardInstruction):
    pass

class GuardInt(GuardInstruction):
    pass

class GuardBool(GuardInstruction):
    pass

class GuardTrue(GuardInstruction):
    pass

class GuardIndex(GuardInstruction):
    def __init__(self, guard_id: int, operand: "ValueInstruction", type_index: int, values_to_keep: list["ValueInstruction"]):
        super().__init__(guard_id, operand, values_to_keep)
        self.type_index = type_index

    def pretty_print(self, value_to_name):
        return f"{self.__class__.__name__}(guard_id={self.guard_id}, operand={value_to_name(self.operand)}, type_index={self.type_index}, values_to_keep=[{', '.join(value_to_name(v) for v in self.values_to_keep)}])"

class ValueInstruction(TraceInstruction):
    def pretty_print(self, value_to_name):
        return f"{value_to_name(self)} = {self.__class__.__name__}"

class ConstantInstruction(ValueInstruction):
    def __init__(self, constant_index, type_index):
        self.constant_index = constant_index
        self.type_index = type_index

    def get_live_values(self):
        return []

    def pretty_print(self, value_to_name):
        return f"{value_to_name(self)} = {self.__class__.__name__}(constant_index={self.constant_index})"

class BinaryOpInstruction(ValueInstruction):
    def __init__(self, left, right, type_index):
        self.left = left
        self.right = right
        self.type_index = type_index

    def get_live_values(self):
        return [self.left, self.right]

    def pretty_print(self, value_to_name):
        return f"{value_to_name(self)} = {self.__class__.__name__}({value_to_name(self.left)}, {value_to_name(self.right)})"

class BoolBinInstruction(BinaryOpInstruction):
    def __init__(self, left, right):
        self.left = left
        self.right = right
        self.type_index = 2

class EqInstruction(BoolBinInstruction):
    pass

class LtInstruction(BoolBinInstruction):
    pass

class GtInstruction(BoolBinInstruction):
    pass

class LeInstruction(BoolBinInstruction):
    pass

class GeInstruction(BoolBinInstruction):
    pass

class NeInstruction(BoolBinInstruction):
    pass

class IntBinInstruction(BinaryOpInstruction):
    def __init__(self, left, right):
        self.left = left
        self.right = right
        self.type_index = 0

class AddInstruction(IntBinInstruction):
    pass

class SubInstruction(IntBinInstruction):
    pass

class MulInstruction(IntBinInstruction):
    pass

class DivInstruction(IntBinInstruction):
    pass

class ModInstruction(IntBinInstruction):
    pass

class InputInstruction(ValueInstruction):
    def __init__(self, input_index):
        self.input_index = input_index

    def get_live_values(self):
        return []

    def pretty_print(self, value_to_name):
        return f"{value_to_name(self)} = {self.__class__.__name__}(input_index={self.input_index})"

class GetFieldInstruction(ValueInstruction):
    def __init__(self, obj, field_index):
        self.obj = obj
        self.field_index = field_index

    def get_live_values(self):
        return [self.obj]

    def pretty_print(self, value_to_name):
        return f"{value_to_name(self)} = {self.__class__.__name__}({value_to_name(self.obj)}, field_index={self.field_index})"

class SetFieldInstruction(TraceInstruction):
    def __init__(self, obj, field_index, value):
        self.obj = obj
        self.field_index = field_index
        self.value = value

    def get_live_values(self):
        return [self.obj, self.value]

    def pretty_print(self, value_to_name):
        return f"{self.__class__.__name__}({value_to_name(self.obj)}, field_index={self.field_index}, value={value_to_name(self.value)})"

class NewInstruction(ValueInstruction):
    def __init__(self, type_index, num_fields):
        self.type_index = type_index
        self.num_fields = num_fields

    def get_live_values(self):
        return []

    def pretty_print(self, value_to_name):
        return f"{value_to_name(self)} = {self.__class__.__name__}(type_index={self.type_index}, num_fields={self.num_fields})"

class Phi(TraceInstruction):
    def __init__(self, input_instruction: InputInstruction, loop_back_operand: ValueInstruction):
        self.input_instruction = input_instruction
        self.loop_back_operand = loop_back_operand

    def get_live_values(self):
        return [self.input_instruction, self.loop_back_operand]

    def pretty_print(self, value_to_name):
        return f"{self.__class__.__name__}(input={value_to_name(self.input_instruction)}, loop_back={value_to_name(self.loop_back_operand)})"

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

    def phi(self, input_instruction, loop_back_operand):
        instruction = Phi(input_instruction, loop_back_operand)
        self.add_instruction(instruction)
        return instruction

    def get_instructions(self):
        return list(self.instructions)

    def optimize(self, constant_table):
        self.remove_redundant_guards()
        self.dead_value_elimination()
        self.optimize_constant_guards(constant_table)

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

    def dead_value_elimination(self):
        used_values = set()
        for instruction in reversed(self.instructions):
            if isinstance(instruction, GuardInstruction):
                used_values.add(instruction.operand)
                used_values.update(instruction.values_to_keep)
            elif isinstance(instruction, SetFieldInstruction):
                used_values.add(instruction.obj)
                used_values.add(instruction.value)
            else:
                used_values.update(instruction.get_live_values())

        optimized_instructions = [
            inst for inst in self.instructions
            if not isinstance(inst, ValueInstruction) or inst in used_values
        ]

        self.instructions = optimized_instructions

    def optimize_constant_guards(self, constant_table):
        optimized_instructions = []
        for instruction in self.instructions:
            if isinstance(instruction, GuardInstruction) and isinstance(instruction.operand, ConstantInstruction):
                constant = constant_table[instruction.operand.constant_index]
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
        for instruction in self.instructions:
            pretty_instructions.append(instruction.pretty_print(get_value_name))

        return "\n".join(pretty_instructions)

def get_liveness_ranges(instructions):
    liveness = {}

    def update_liveness(value, idx):
        start, end = liveness[value]
        liveness[value] = (start, max(end, idx))

    for idx, inst in enumerate(instructions):
        # Because there are no cycles and only ValueInstructions can
        # be operands, this is the first time we will have seen this value
        if isinstance(inst, ValueInstruction):
            liveness[inst] = (idx, idx)

        # Now we can just find all operands and update the max on them
        for value in inst.get_live_values():
            update_liveness(value, idx)

    return liveness

def allocate_registers(instructions, available_registers):
    liveness_ranges = get_liveness_ranges(instructions)
    register_allocation = {}
    used_registers = set()

    for idx, inst in enumerate(instructions):
        for value in inst.get_live_values():
            if liveness_ranges[value][1] == idx:
                reg = register_allocation[value]
                if reg in used_registers:
                    used_registers.remove(reg)

        if isinstance(inst, ValueInstruction):
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
