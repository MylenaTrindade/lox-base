#!/usr/bin/env python3

from lox.ast import Super, This

# Test the dataclass creation
try:
    super_node = Super()
    print(f"Super node created: {super_node}")
    print(f"Super annotations: {getattr(super_node, '__annotations__', 'NOT FOUND')}")
    
    this_node = This()
    print(f"This node created: {this_node}")
    print(f"This annotations: {getattr(this_node, '__annotations__', 'NOT FOUND')}")
    
    # Test children method
    print(f"Super children: {list(super_node.children())}")
    print(f"This children: {list(this_node.children())}")
    
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
