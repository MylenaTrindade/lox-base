#!/usr/bin/env python3

from lox.parser import parse

src = '''fun returnArg(arg) {
  return arg;
}'''

try:
    result = parse(src)
    print("Parsing succeeded, tree:")
    print(result.pretty())
except Exception as e:
    print(f"Parsing failed with: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
