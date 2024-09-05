from trax_obj import TraxObject
from trax_tracing import *
from typing import Tuple, Any, Callable
from trax_backend import AppleSiliconBackend
from dataclasses import dataclass
import trax_bc_compile as bc

@dataclass
class InterpValue:
    concrete: TraxObject
    trace: ValueInstruction #| None # TODO: Can I just always trace?

MethodKey = Tuple[int, str]
ProgramKey = Tuple[MethodKey, int]

class GuardException(Exception):
    def __init__(self, guard_instruction, values, kwargs):
        self.guard_instruction = guard_instruction
        self.values = values
        self.kwargs = kwargs
        super().__init__(f"Guard failed: {guard_instruction}")

@dataclass
class Frame:
    vars: list[TraxObject]
    stack: list[InterpValue]
    pgrm: ProgramKey
    trace_frame_idx: int | None = None

    def activate_trace(self):
        # We should only activate a trace when
        # the stack is empty
        assert len(self.stack) == 0
        self.trace_active = 0

    def to_trace_frame(self) -> "TraceFrame":
        # The trace needs to be active when we call this method
        assert self.trace_active
        # The assert below might fail if a trace is started while the
        # stack is not empty but should pass if the stack was empty
        stack = [v.trace for v in self.stack if v.trace is not None]
        assert len(stack) == len(self.stack)
        return TraceFrame(len(self.vars), stack, self.pgrm)

@dataclass
class TraceFrame:
    num_vars: int
    stack: list[ValueInstruction]
    pgrm: ProgramKey

@dataclass
class BuiltinMethod:
    interp: Callable[[list[TraxObject]], TraxObject]
    trace: Callable[[TraceCompiler, list[ValueInstruction]], ValueInstruction]

@dataclass
class GuardHandler:
    frames: list[TraceFrame]
    values_to_keep: list[ValueInstruction]

@dataclass
class TraceInfo:
    exec_counts: dict[ProgramKey, int]
    cached_traces: dict[ProgramKey, TraceCompiler]
    guard_handler:

@dataclass
class Interpreter:
    # call_stack[-1] is the current frame
    call_stack: list[Frame]

    # User defined methods (constant)
    methods: dict[MethodKey, list[bc.Instruction]]

    # Non-user defiend methods. Some of these are traceable
    # If a builtin is not traceable then we (constant)
    builtin_methods: dict[MethodKey, BuiltinMethod]

    # This is needed for executing traces and allocating
    # objects
    backend: AppleSiliconBackend

    # Things we need for tracing
    # TODO:
        # Right now we have the following indications of tracing:
        # * trace_key is not None
        # * frame.trace_frame_idx is not None
        # * values in frame.stack have trace values
        # * self.trace_compiler is not None (derived at least)
        #
        # It would be a lot nicer if there was a single check that was
        # simple enough that it told even pyright "yeah we're all good"
        # when manipulating trace stuff
    trace_threshold: int
    trace_key: ProgramKey | None # TODO: Can we simplify?
    compiled_traces: dict[ProgramKey, TraceCompiler] # TODO: Can we simplify?
    jump_counts: dict[ProgramKey, int]
    guard_handlers: list[GuardHandler] # TODO: Can we simplify?

    @property
    def frame(self) -> Frame:
        return self.call_stack[-1]

    @property
    def trace_compiler(self) -> TraceCompiler:
        if self.trace_key in self.compiled_traces:
            return self.compiled_traces[self.trace_key]
        return TraceCompiler()

    def cancel_trace(self):
        assert self.trace_key
        # This basically blacklists this trace
        # at least for a while. Ideally I'd like
        # some sort of exponential backoff or something
        self.jump_counts[self.trace_key] = -(2 ** 16)
        del self.compiled_traces[self.trace_key]
        self.trace_key = None

    # TODO: This is actully never used? wild
    # def value_inst(self, inst, num_args):
    #     """
    #     Performs both the tracing and computation associated with a value
    #     instruction
    #     """
    #     args = [self.frame.stack.pop() for _ in range(num_args)]
    #     value_inst = inst([arg.trace for arg in args])
    #     value: TraxObject = value_inst.interp([arg.concrete for arg in args])
    #     if self.trace_compiler:
    #         self.trace_compiler.add_instruction(value_inst)
    #     else:
    #         value_inst = None
    #     self.frame.stack.append(InterpValue(value, value_inst))

    def values_to_keep(self):
        """
        This finds all traced values that need to be returned
        """
        values = set() # Use a set to dedup traced values
        for frame in reversed(self.call_stack):
            if frame.trace_active is None:
                break
            for value in frame.stack:
                values.add(value.trace)

        return list(values)

    def new_guard_id(self):
        """
        If a trace is active create a new guard handler and return it
        """
        assert self.trace_key
        frames = []
        for frame in reversed(self.call_stack):
            if frame.trace_active is None:
                break
            frames.append(frame.to_trace_frame())
        handler = GuardHandler(frames, self.values_to_keep())
        guard_id = len(self.guard_handlers)
        self.guard_handlers.append(handler)
        return guard_id

    def check_guard(self, inst, *args, **kwargs):
        """
        Checks a guard for a particular instruction. Is generally
        a noop for the interpreter but is very important for tracing
        """
        values = [arg.concrete for arg in args]
        if inst.check(values, **kwargs):
            raise GuardException(inst, values, kwargs)
        trace_values = [arg.trace for arg in args if arg.trace]
        guard_id = self.new_guard_id()
        values_to_keep = self.values_to_keep()
        self.trace_compiler.add_instruction(inst(guard_id, *args, values_to_keep, **kwargs))

    def call_builtin(self, builtin: BuiltinMethod, args: list[InterpValue]):
        args_concrete = [arg.concrete for arg in args]
        value = builtin.interp(args_concrete)
        trace_args = [arg.trace for arg in args]
        value_inst = builtin.trace(self.trace_compiler, trace_args)
        self.frame.stack.append(InterpValue(value, value_inst))

    def exec_PushConst(self, instruction: bc.PushConst):
        trace_inst = ConstantInstruction(instruction.constant)
        self.trace_compiler.add_instruction(trace_inst)
        self.frame.stack.append(InterpValue(instruction.constant, trace_inst))

    def exec_Pop(self, instruction: bc.Pop):
        self.frame.stack.pop()

    def exec_Call(self, instruction: bc.Call):
        # TODO: Add a guard check
        args = [self.frame.stack.pop() for _ in range(instruction.num_args)]
        args.reverse()
        obj = self.frame.stack.pop()
        type_index = obj.concrete.get_type_index()
        method_key = (type_index, instruction.method_name)

        # If this is a builtin then we handle that a bit differently
        if method_key in self.builtin_methods:
            self.call_builtin(self.builtin_methods[method_key], args)
            return

        # Calculate optional trace frame idx
        trace_frame_idx = None if self.frame.trace_frame_idx is None else self.frame.trace_frame_idx + 1

        # We can start off with vars empty and dynamicly size them
        frame = Frame([obj.concrete], args, (method_key, 0), trace_frame_idx)
        self.call_stack.append(frame)

    def exec_Jmp(self, instruction: bc.Jmp):
        # TODO: finish the trace
        assert len(self.frame.stack) == 0
        self.jump_counts[self.frame.pgrm] = self.jump_counts.get(self.frame.pgrm, 0) + 1
        if self.jump_counts[self.frame.pgrm] >= self.trace_threshold and self.trace_key is None:
            self.trace_key = self.frame.pgrm
            self.compiled_traces[self.trace_key] = TraceCompiler()
            self.frame.activate_trace()
        return instruction.target

    def exec_JmpIfNot(self, instruction: bc.JmpIfNot):
        condition = self.frame.stack.pop()
        if not condition.concrete.to_bool():
            return instruction.target
        return None

    def exec_GetField(self, instruction: bc.GetField):
        value = self.frame.stack.pop()
        out = value.concrete.get_field(instruction.field_index)

        value_inst = GetFieldInstruction(value.trace, instruction.field_index)
        self.trace_compiler.add_instruction(value_inst)

        self.frame.stack.append(InterpValue(out, value_inst))

    def exec_SetField(self, instruction: bc.SetField):
        obj = self.frame.stack.pop()
        value = self.frame.stack.pop()
        obj.concrete.set_field(instruction.field_index, value)
        self.trace_compiler.add_instruction(SetFieldInstruction(obj.trace, instruction.field_index, value.trace))

    def exec_New(self, instruction: bc.New):
        args = [self.frame.stack.pop() for _ in range(instruction.num_fields)]
        args.reverse()
        args_concrete = [arg.concrete for arg in args]
        obj = self.backend.new(instruction.type_index, args_concrete)
        trace_inst = NewInstruction(instruction.type_index, instruction.num_fields)
        self.trace_compiler.add_instruction(trace_inst)
        self.frame.stack.append(InterpValue(obj, trace_inst))

    def exec_Return(self, instruction: bc.Return):
        return_value = self.frame.stack.pop()
        self.call_stack.pop()
        self.frame.stack.append(return_value)

    def exec_GetVar(self, instruction: bc.GetVar):
        assert instruction.var_index < len(self.frame.vars)
        trace = GetVar(self.frame.trace_active, instruction.var_index)
        self.trace_compiler.add_instruction(trace)
        self.frame.stack.append(InterpValue(self.frame.vars[instruction.var_index], trace))

    def exec_SetVar(self, instruction: bc.SetVar):
        # Dynamically size variable space
        if instruction.var_index >= len(self.frame.vars):
            diff = len(self.frame.vars) - instruction.var_index
            self.frame.vars.extend([TraxObject(TraxObject.nil)] * diff)

        value = self.frame.stack.pop()
        self.trace_compiler.add_instruction(SetVar(self.frame.trace_active, instruction.var_index, value.trace))
        self.frame.vars[instruction.var_index] = value.concrete

    def dispatch(self):
        while self.call_stack:
            method_key, pc = self.frame.pgrm
            instructions = self.methods[method_key]
            if pc >= len(instructions):
                raise ValueError(f"PC out of bounds: {pc} >= {len(instructions)}")
            instruction = instructions[pc]
            exec_method = getattr(self, f"exec_{type(instruction).__name__}")
            result = exec_method(instruction)
            if isinstance(result, int):
                pc = result
            else:
                pc += 1
            self.frame.pgrm = (method_key, pc)
