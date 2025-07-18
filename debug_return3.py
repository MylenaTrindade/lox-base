#!/usr/bin/env python3

from lox.parser import parse
from lox.ast import Function

src = '''fun returnArg(arg) {
  return arg;
}'''

def debug_validate_self(self, cursor):
    print(f"Validating Return statement")
    
    current = cursor.parent_cursor
    enclosing_function = None
    
    while current is not None:
        node = current.node
        print(f"  Checking node: {type(node).__name__} - {node}")
        print(f"  Is Function?: {isinstance(node, Function)}")
        print(f"  Function class: {Function}")
        print(f"  Node class: {type(node)}")
        
        if isinstance(node, Function):
            if enclosing_function is None:
                enclosing_function = node
                print(f"  Found enclosing function: {enclosing_function}")
        current = current.parent_cursor
    
    print(f"Final enclosing_function: {enclosing_function}")
    if enclosing_function is None:
        print("ERROR: No enclosing function found!")
    
    return  # Skip the actual validation

# Monkey patch
from lox.ast import Return
Return.validate_self = debug_validate_self

try:
    result = parse(src)
    print("Parsing succeeded")
except Exception as e:
    print(f"Parsing failed with: {type(e).__name__}: {e}")
