#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/home/mylena/lox-base')

from lox.testing import Example
from pathlib import Path

path = Path('/home/mylena/lox-base/exemplos/operator/add_bool_num.lox')
content = path.read_text(encoding="utf-8")
print("File content:")
print(content)
print()

ex = Example(content, path=path, fuzzy=False)
print("Parsed example:")
print(f"src: {repr(ex.src)}")
print(f"error: {ex.error}")
print(f"expect_runtime_error: {ex.expect_runtime_error}")
print(f"outputs: {ex.outputs}")
print()

try:
    ctx, stdout, err = ex.eval()
    print(f"stdout: {repr(stdout)}")
    print(f"err: {repr(err)}")
except Exception as e:
    print(f"Exception during eval: {e}")
