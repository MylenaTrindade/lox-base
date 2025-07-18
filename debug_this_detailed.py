#!/usr/bin/env python3

from pathlib import Path
from lark import Lark
from lox.transformer import LoxTransformer

DIR = Path(__file__).parent / "lox"
GRAMMAR_PATH = DIR / "grammar.lark"

parser = Lark(GRAMMAR_PATH.read_text(), start="program")
transformer = LoxTransformer()

src = "this;"

try:
    tree = parser.parse(src)
    print("Parse tree:")
    print(tree.pretty())
    print("\nTransforming...")
    result = transformer.transform(tree)
    print("Transformed tree:")
    print(result)
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
