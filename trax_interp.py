from trax_obj import TraxObject
from trax_tracing import InputInstruction, TraceCompiler, ValueInstruction
from typing import Tuple, Any, Callable
from trax_backend import AppleSiliconBackend

class StackFrame:
    def __init__(self, method_key: "MethodKey", pc: int, stack: list[TraxObject]):
        self.method_key  = method_key
        self.pc= pc
        self.stack  = stack

class GuardFrame:
    def __init__(self, method_key, pc, trace_stack):
        self.method_key: MethodKey = method_key
        self.pc: int = pc
        self.trace_stack: list[ValueInstruction] = trace_stack

class GuardHandler:
    def __init__(self, frame: GuardFrame, guard_frames: list[GuardFrame], values_to_keep: list[ValueInstruction]):
        self.frame = frame
        self.guard_frames = guard_frames
        self.values_to_keep = values_to_keep

MethodKey = Tuple[int, str]
ProgramKey = Tuple[MethodKey, int]

class Interpreter:
    constants: list[TraxObject]
    method_map: dict[MethodKey, list[dict]]
    stack: list[TraxObject]
    method_key: MethodKey
    pc: int
    code: list[dict]
    call_stack: list[StackFrame]
    builtin_methods: dict[MethodKey, Callable]
    builtin_trace_methods: dict[MethodKey, Callable]

    jump_counts: dict[ProgramKey, int]
    trace_compiler: TraceCompiler
    trace_stack: list[ValueInstruction]
    compiled_traces: dict[ProgramKey, Any]
    guard_handlers: list[GuardHandler]
    trace_call_stack: list[GuardFrame]
    backend: AppleSiliconBackend

    def __init__(self, constants, method_map, trace_threshold=2):
        # Mappings from the bytecode compiler
        self.constants = constants
        self.method_map = method_map

        # The current frame's stack
        self.stack = []

        # Current method and pc
        self.method_key = (-1, "<bad method>")
        self.pc = -1
        self.code = []

        # Frames we need to jump back to on return
        self.call_stack = []

        # Mappings of builtin methods to implementations
        self.builtin_methods = {}
        self.builtin_trace_methods = {}

        # Tracing stuff
        self.jump_counts = {} # Counts how many times we've jumped to a trace
        self.trace_compiler = TraceCompiler() # The current trace compiler
        self.trace_active = None # The entry point for the current trace
        self.trace_threshold = trace_threshold # How many jumps to a location we need to start tracing
        self.trace_stack = [] # This is a simulated stack of ValueInstructions
        self.compiled_traces = {} # Once a trace is complete we compile it and add it here
        self.guard_handlers = [] # A mapping of guard_ids to guard handlers
        self.trace_call_stack = [] # A simulated call stack that helps us emit guard handlers

        # Backend for trace compilation
        self.backend = AppleSiliconBackend()
        self.const_table = self.backend.const_table(self.constants)

    def new_guard_handler(self, pc=None):
        if pc is None:
            pc = self.pc
        values_to_keep = self.compute_trace_exit_values()
        frame = GuardFrame(self.method_key, pc, list(self.trace_stack))
        handler = GuardHandler(frame, list(self.trace_call_stack), values_to_keep)
        guard_id = len(self.guard_handlers)
        self.guard_handlers.append(handler)
        return guard_id, values_to_keep

    def add_builtin_method(self, type_index, method_name, func, trace_func):
        self.builtin_methods[(type_index, method_name)] = func
        self.builtin_trace_methods[(type_index, method_name)] = trace_func

    def run(self, obj: TraxObject, initial_function: str, *args):
        type_index = obj.get_type_index()
        self.method_key = (type_index, initial_function)
        self.code = self.method_map.get(self.method_key, [])
        for inst in self.code:
            print(inst)
        if not self.code:
            raise ValueError(f"Function {initial_function} not found for type index {type_index}")
        self.pc = 0

        # Push arguments onto the stack
        self.stack.append(obj)
        self.stack.extend(args)

        while True:
            if self.pc >= len(self.code):
                raise ValueError("Function ended without returning")

            # TODO: check if we can jump into a trace
            program_key = (self.method_key, self.pc)
            if program_key in self.compiled_traces:
                print("Entering trace: ", program_key)
                func = self.compiled_traces[program_key]
                max_values_to_keep = max(len(h.values_to_keep) for h in self.guard_handlers)
                guard_id, return_values = self.backend.call_function(func, self.stack, self.const_table, max_values_to_keep)
                print(f"Exiting trace: {guard_id=}")
                guard_handler = self.guard_handlers[guard_id]
                value_mapping: dict[ValueInstruction, TraxObject] = {}
                for value, obj in zip(guard_handler.values_to_keep, return_values, strict=False):
                    value_mapping[value] = obj

                # Restore program location
                self.pc = guard_handler.frame.pc
                self.method_key = guard_handler.frame.method_key
                self.code = self.method_map[self.method_key]
                print("Now at: ", self.method_key, self.pc, self.code[self.pc])

                # Restore the stack
                self.stack = []
                for value in guard_handler.frame.trace_stack:
                    self.stack.append(value_mapping[value])

                # Restore the call_stack
                self.call_stack = []
                for frame in guard_handler.guard_frames:
                    stack = []
                    for value in frame.trace_stack:
                        stack.append(value_mapping[value])
                    self.call_stack.append(StackFrame(frame.method_key, frame.pc, stack))

            instruction = self.code[self.pc]
            opcode = instruction['opcode']
            self.pc += 1

            print("trace: ", self.method_key, self.pc, instruction, self.stack)
            method = getattr(self, f"execute_{opcode}", None)
            if method:
                result = method(instruction)
                if result is not None:
                    return result
            else:
                raise ValueError(f"Unknown opcode: {opcode}")

    def execute_push_const(self, instruction):
        const_index = instruction['const_index']
        value = self.constants[const_index]
        self.stack.append(value)
        if self.trace_active is not None:
            v = self.trace_compiler.constant(const_index, value.get_type_index())
            self.trace_stack.append(v)

    def execute_dup(self, instruction):
        k = instruction['k']
        value = self.stack[-k-1]
        self.stack.append(value)
        if self.trace_active is not None:
            self.trace_stack.append(self.trace_stack[-k-1])

    def execute_pop(self, instruction):
        self.stack.pop()
        if self.trace_active is not None:
            self.trace_stack.pop()

    def execute_set(self, instruction):
        k = instruction['k']
        value = self.stack.pop()
        self.stack[-k-1] = value
        if self.trace_active is not None:
            v = self.trace_stack.pop()
            self.trace_stack[-k-1] = v

    def compute_trace_exit_values(self):
        values_to_restore = list(self.trace_stack)
        for guard_frame in self.trace_call_stack:
            values_to_restore.extend(guard_frame.trace_stack)
        return values_to_restore

    def emit_guard_index(self, value: ValueInstruction, type_index: int):
        guard_id, values_to_keep = self.new_guard_handler()
        if type_index == 0:
            self.trace_compiler.guard_int(guard_id, value, values_to_keep)
        elif type_index == 1:
            self.trace_compiler.guard_nil(guard_id, value, values_to_keep)
        elif type_index == 2:
            self.trace_compiler.guard_bool(guard_id, value, values_to_keep)
        else:
            self.trace_compiler.guard_index(guard_id, value, type_index, values_to_keep)
        return guard_id

    def emit_guard_true(self, value: ValueInstruction, pc=None):
        guard_id, values_to_keep = self.new_guard_handler(pc=pc)
        self.trace_compiler.guard_true(guard_id, value, values_to_keep)

    def execute_call(self, instruction):
        # NOTE: If we enter a function already in the call stack
        #       we should cancel the trace
        # NOTE: If the trace gets too long we should cancel the trace
        method_name = instruction['method_name']
        num_args = instruction['num_args']
        args = [self.stack.pop() for _ in range(num_args)]
        obj = self.stack.pop()
        type_index = obj.get_type_index()
        function_key = (type_index, method_name)

        # Add a guard for this method
        if self.trace_active is not None:
            # NOTE: it would be great if we decided between this check
            #       and inline caching in the future. inline caching is
            #       great for more dynamic code
            # TODO: The guard needs the values it has to save passed to it
            trace_obj = self.trace_stack[-num_args-1]
            self.emit_guard_index(trace_obj, type_index)

        # We need to handle builtins a bit differently from other things
        if function_key in self.builtin_methods:
            # Call the built-in method
            result = self.builtin_methods[function_key](obj, *reversed(args))
            self.stack.append(result)
            if self.trace_active is not None:
                trace_compiler = self.trace_compiler
                trace_func = self.builtin_trace_methods[function_key]
                trace_args = [self.trace_stack.pop() for _ in range(num_args)]
                trace_obj = self.trace_stack.pop()
                print(self, trace_obj, trace_args)
                v = trace_func(self, trace_obj, *reversed(trace_args))
                self.trace_stack.append(v)
            return

        # In the more standard case of this just being a user defined method
        # we just have to add a stack frame and then update code, pc, and method
        if function_key in self.method_map:
            frame = StackFrame(self.method_key, self.pc, self.stack)
            self.call_stack.append(frame)
            self.method_key = function_key
            self.code = self.method_map[function_key]
            print(f"entering method: {self.method_key}")
            for opcode in self.code:
                print(opcode)
            self.pc = 0
            self.stack = [obj] + list(reversed(args))
            print("stack: ", self.stack)
            if self.trace_active is not None:
                frame = GuardFrame(function_key, self.pc, self.trace_stack)
                self.trace_call_stack.append(frame)
            return

        raise ValueError(f"Method {method_name} not found for type {type_index}")

    def execute_jmp(self, instruction):
        offset = instruction['offset']
        target_pc = self.pc + offset
        # We only want to tag this as a loop back if there's something looping back here
        function_key = ()
        if instruction['loop_back']:
            self.increment_jump_count((self.method_key, target_pc))
        self.pc = target_pc

    def execute_jmp_if_not(self, instruction):
        condition = self.stack.pop()
        offset = instruction['offset']
        target_pc = self.pc + offset
        if self.trace_active is not None:
            self.emit_guard_true(self.trace_stack.pop(), pc=target_pc)
        if condition.is_false():
            self.pc = target_pc

    def execute_get_field(self, instruction):
        field_index = instruction['field_index']
        obj = self.stack.pop()
        value = obj.get_field(field_index)
        self.stack.append(value)
        if self.trace_active is not None:
            obj = self.trace_stack.pop()
            v = self.trace_compiler.get_field(obj, field_index)
            self.trace_stack.append(v)

    def execute_set_field(self, instruction):
        field_index = instruction['field_index']
        obj = self.stack.pop()
        value = self.stack.pop()
        obj.set_field(field_index, value)
        if self.trace_active is not None:
            obj = self.trace_stack.pop()
            value = self.trace_stack.pop()
            self.trace_compiler.set_field(obj, field_index, value)

    def execute_new(self, instruction):
        type_index = instruction['type_index']
        num_fields = instruction['num_fields']
        fields = [self.stack.pop() for _ in range(num_fields)]
        obj = TraxObject.new(type_index, list(reversed(fields)))
        self.stack.append(obj)
        if self.trace_active is not None:
            args = [self.trace_stack.pop() for _ in range(num_fields)]
            v = self.trace_compiler.new(type_index, num_fields)
            for field_index, field_value in enumerate(reversed(args)):
                self.trace_compiler.set_field(v, field_index, field_value)
            self.trace_stack.append(v)

    def execute_return(self, instruction):
        v = self.stack.pop()
        if not self.call_stack:
            return v
        frame = self.call_stack.pop()
        self.method_key = frame.method_key
        self.pc = frame.pc
        self.stack = frame.stack
        self.stack.append(v)
        self.code = self.method_map[frame.method_key]
        print("returning to: ", frame.method_key, frame.pc, frame.stack)
        if self.trace_active is not None:
            trace_value = self.trace_stack.pop()
            guard_frame = self.trace_call_stack.pop()
            assert guard_frame.method_key == frame.method_key
            assert guard_frame.pc == frame.pc
            self.trace_stack = guard_frame.trace_stack
            self.trace_stack.append(trace_value)

    def get_stack(self):
        return self.stack

    def increment_jump_count(self, key: ProgramKey):
        if key in self.compiled_traces:
            return
        self.jump_counts[key] = self.jump_counts.get(key, 0) + 1
        if self.jump_counts[key] > self.trace_threshold and self.trace_active is None:
            # Set all tracing state to start tracing
            self.trace_active = key
            self.trace_compiler = TraceCompiler()
            trace_stack: list[InputInstruction] = [self.trace_compiler.input(i) for i in range(len(self.stack))]
            self.trace_stack = list(trace_stack)
            self.trace_inputs = trace_stack
            self.trace_call_stack = []
        elif self.trace_active == key:
            # We have to close the loop on the inputs
            for input, value in zip(self.trace_inputs, self.trace_stack, strict=True):
                input.phi = value
            self.trace_compiler.optimize(self.constants)
            print(self.trace_compiler.pretty_print())
            print("\n")
            compiled_trace = self.backend.compile_trace(self.trace_compiler, self.constants)
            print(compiled_trace.hex(), flush=True)
            compiled_trace = self.backend.create_executable_memory(compiled_trace)
            self.trace_compiler = TraceCompiler()
            self.compiled_traces[key] = compiled_trace
            self.trace_active = None
            self.trace_stack = []
            self.trace_call_stack = []

    def compile_trace(self, trace):
        bytes = self.backend.compile_trace(trace, self.constants)
        return self.backend.create_executable_memory(bytes)
