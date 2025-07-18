#!/usr/bin/env python3

from lox.parser import parse

# Use o arquivo completo que está falhando
src = '''fun returnArg(arg) {
  return arg;
}

fun returnFunCallWithArg(func, arg) {
  return returnArg(func)(arg);
}

fun printArg(arg) {
  print arg;
}

returnFunCallWithArg(printArg, "hello world");'''

def debug_validate_self(self, cursor):
    print(f"Validating Return statement: {self}")
    
    current = cursor.parent_cursor
    enclosing_function = None
    
    while current is not None:
        node = current.node
        print(f"  Checking node: {type(node).__name__}")
        
        if isinstance(node, Function):
            if enclosing_function is None:
                enclosing_function = node
                print(f"  Found enclosing function: {enclosing_function.name}")
        current = current.parent_cursor
    
    print(f"Final enclosing_function: {enclosing_function}")
    if enclosing_function is None:
        print("ERROR: No enclosing function found!")
        
        # Let's check what we actually have
        print("Full cursor path:")
        current = cursor
        while current is not None:
            print(f"  {type(current.node).__name__}: {current.node}")
            current = current.parent_cursor
    
    return  # Skip the actual validation

# Monkey patch
from lox.ast import Return, Function
Return.validate_self = debug_validate_self

try:
    result = parse(src)
    print("Parsing succeeded")
except Exception as e:
    print(f"Parsing failed with: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
