from trax_obj import  TraxObject
import trax_interp
from trax_tracing import *
from trax_trace_interp import TraceInterpreter
from abc import ABC, abstractmethod

class InterpInterface(ABC):
    @abstractmethod
    def emit_guard_index(self, operand: ValueInstruction, type_index: int):
        ...

    @property
    @abstractmethod
    def trace_compiler(self) -> TraceCompiler:
        ...

class InterpFacade:
    def __init__(self, trace_compiler):
        self.trace_compiler = trace_compiler

    def emit_guard_index(self, operand: ValueInstruction, type_index: int):
        if type_index == 0:
            self.trace_compiler.guard_int(-1, operand, [])
        elif type_index == 1:
            self.trace_compiler.guard_nil(-1, operand, [])
        elif type_index == 2:
            self.trace_compiler.guard_bool(-1, operand, [])
        else:
            self.trace_compiler.guard_index(-1, operand, type_index, [])
        return -1

InterpInterface.register(InterpFacade)
InterpInterface.register(trax_interp.Interpreter)

class IntegerMethods:
    @staticmethod
    def add_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        interp.emit_guard_index(arg2, 0)
        return tc.add(arg1, arg2)

    @staticmethod
    def sub_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        interp.emit_guard_index(arg2, 0)
        return tc.sub(arg1, arg2)

    @staticmethod
    def mul_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        interp.emit_guard_index(arg2, 0)
        return tc.mul(arg1, arg2)

    @staticmethod
    def div_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        interp.emit_guard_index(arg2, 0)
        return tc.div(arg1, arg2)

    @staticmethod
    def mod_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        interp.emit_guard_index(arg2, 0)
        return tc.mod(arg1, arg2)

    @staticmethod
    def lt_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        interp.emit_guard_index(arg2, 0)
        return tc.lt(arg1, arg2)

    @staticmethod
    def gt_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        interp.emit_guard_index(arg2, 0)
        return tc.gt(arg1, arg2)

    @staticmethod
    def le_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        interp.emit_guard_index(arg2, 0)
        return tc.le(arg1, arg2)

    @staticmethod
    def ge_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        interp.emit_guard_index(arg2, 0)
        return tc.ge(arg1, arg2)

    @staticmethod
    def eq_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        interp.emit_guard_index(arg2, 0)
        return tc.eq(arg1, arg2)

    @staticmethod
    def ne_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        interp.emit_guard_index(arg2, 0)
        return tc.ne(arg1, arg2)

    @staticmethod
    def min_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        interp.emit_guard_index(arg2, 0)
        return tc.min(arg1, arg2)

    @staticmethod
    def max_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        interp.emit_guard_index(arg2, 0)
        return tc.max(arg1, arg2)

    @staticmethod
    def to_bool_trace(interp: InterpInterface, arg1: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 0)
        return tc.int_to_bool(arg1)

    @staticmethod
    def interpreter_builtin(instruction_name):
        def builtin(*args):
            trace_compiler = TraceCompiler()
            interp_facade = InterpFacade(trace_compiler)
            trace_args = [trace_compiler.input(i) for i in range(len(args))]
            print(interp_facade, trace_args, args)
            result = getattr(IntegerMethods, f"{instruction_name}_trace")(interp_facade, *trace_args)
            trace_interpreter = TraceInterpreter([])
            return trace_interpreter.interpret(trace_compiler.get_instructions(), args, result)
        return builtin

    @staticmethod
    def add_methods_to_interpreter(interpreter: trax_interp.Interpreter):
        method_mapping = {
            'add': '+', 'sub': '-', 'mul': '*', 'div': '/', 'mod': '%',
            'lt': '<', 'gt': '>', 'le': '<=', 'ge': '>=', 'eq': '==', 'ne': '!=',
            'min': 'min', 'max': 'max', 'to_bool': 'to_bool'
        }
        for alpha_name, symbol in method_mapping.items():
            interpreter.add_builtin_method(0, symbol, IntegerMethods.interpreter_builtin(alpha_name), getattr(IntegerMethods, f"{alpha_name}_trace"))

class BooleanMethods:
    @staticmethod
    def and_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 2)
        interp.emit_guard_index(arg2, 2)
        return tc.logical_and(arg1, arg2)

    @staticmethod
    def or_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 2)
        interp.emit_guard_index(arg2, 2)
        return tc.logical_or(arg1, arg2)

    @staticmethod
    def not_trace(interp: InterpInterface, arg1: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 2)
        return tc.logical_not(arg1)

    @staticmethod
    def eq_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 2)
        interp.emit_guard_index(arg2, 2)
        return tc.eq(arg1, arg2)

    @staticmethod
    def ne_trace(interp: InterpInterface, arg1: ValueInstruction, arg2: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 2)
        interp.emit_guard_index(arg2, 2)
        return tc.ne(arg1, arg2)

    @staticmethod
    def to_int_trace(interp: InterpInterface, arg1: ValueInstruction):
        tc = interp.trace_compiler
        interp.emit_guard_index(arg1, 2)
        return tc.bool_to_int(arg1)

    @staticmethod
    def interpreter_builtin(instruction_name):
        def builtin(*args):
            trace_compiler = TraceCompiler()
            interp_facade = InterpFacade(trace_compiler)
            trace_args = [trace_compiler.input(i) for i in range(len(args))]
            result = getattr(BooleanMethods, f"{instruction_name}_trace")(interp_facade, *trace_args)
            trace_interpreter = TraceInterpreter([])
            return trace_interpreter.interpret(trace_compiler.get_instructions(), args, result)
        return builtin

    @staticmethod
    def add_methods_to_interpreter(interpreter: trax_interp.Interpreter):
        method_mapping = {
            'and': '&', 'or': '|', 'not': '!', 'eq': '==', 'ne': '!=', 'to_int': 'to_int'
        }
        for alpha_name, symbol in method_mapping.items():
            interpreter.add_builtin_method(2, symbol, BooleanMethods.interpreter_builtin(alpha_name), getattr(BooleanMethods, f"{alpha_name}_trace"))

class DefaultRuntime:
    @staticmethod
    def add_methods_to_interpreter(interpreter: trax_interp.Interpreter):
        IntegerMethods.add_methods_to_interpreter(interpreter)
        BooleanMethods.add_methods_to_interpreter(interpreter)
        # Future method collections can be added here
