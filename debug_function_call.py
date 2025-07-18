#!/usr/bin/env python3

from lox.parser import parse
from lox.ctx import Ctx

# Test simple function call
code = """
fun printFields() {
  print "test";
}
printFields();
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
