#!/usr/bin/env python3

from lox.parser import parse
from lox.node import Cursor

src = '''fun returnArg(arg) {
  return arg;
}'''

def debug_cursor_path(cursor):
    """Debug function to print the cursor path"""
    path = []
    current = cursor
    while current is not None:
        path.append(f"{type(current.node).__name__}")
        current = current.parent_cursor
    return " -> ".join(reversed(path))

# Monkey patch the validate_self method to add debugging
from lox.ast import Return

original_validate = Return.validate_self

def debug_validate_self(self, cursor):
    print(f"Validating Return statement")
    print(f"Cursor path: {debug_cursor_path(cursor)}")
    
    current = cursor.parent_cursor
    while current is not None:
        print(f"  Checking node: {type(current.node).__name__}")
        current = current.parent_cursor
    
    return original_validate(self, cursor)

Return.validate_self = debug_validate_self

try:
    result = parse(src)
    print("Parsing succeeded")
except Exception as e:
    print(f"Parsing failed with: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
