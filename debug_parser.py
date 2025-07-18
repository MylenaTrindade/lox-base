#!/usr/bin/env python3

from pathlib import Path
from lark import Lark

# Use only the problematic line
src = 'returnFunCallWithArg(printArg, "hello world");'

print(f"Source: {src}")

# Parse with the raw grammar first
lox_dir = Path("lox")
grammar_path = lox_dir / "grammar.lark"
grammar = grammar_path.read_text()
parser = Lark(grammar, start="program", parser="lalr")

print("\n=== Raw Parse Tree ===")
tree = parser.parse(src)
print(tree.pretty())

print("\n=== After Transformation ===")
from lox.transformer import LoxTransformer
transformer = LoxTransformer()
ast = transformer.transform(tree)
print(ast)
print(f"AST type: {type(ast)}")

if hasattr(ast, 'stmts'):
    print(f"Number of statements: {len(ast.stmts)}")
    for i, stmt in enumerate(ast.stmts):
        print(f"  Statement {i}: {type(stmt).__name__} - {stmt}")
