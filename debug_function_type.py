#!/usr/bin/env python3

from lox.parser import parse
from lox.ctx import Ctx

# Test what type a function variable has
code = """
fun foo() {}
print foo;
"""

print("Parsing...")
ast = parse(code)
print("AST:", ast)

print("\nEvaluating...")
ctx = Ctx()
try:
    result = ast.eval(ctx)
    print("Result:", result)
    print("Type of foo:", type(ctx["foo"]))
    print("foo:", ctx["foo"])
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()
