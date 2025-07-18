#!/usr/bin/env python3

from lox.parser import parse
from lox.ctx import Ctx

# Test simple field assignment
code = """
class A {}
var a = A();
a.foo = "test";
print a.foo;
"""

print("Parsing...")
ast = parse(code)
print("AST:", ast)

print("\nEvaluating...")
ctx = Ctx()
try:
    result = ast.eval(ctx)
    print("Result:", result)
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()
