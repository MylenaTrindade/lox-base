#!/usr/bin/env python3

from lox.parser import parse

src = "this; // Error at 'this': Can't use 'this' outside of a class."

try:
    result = parse(src)
    print("Parsing succeeded, tree:")
    print(result)
except Exception as e:
    print(f"Parsing failed with: {type(e).__name__}: {e}")
