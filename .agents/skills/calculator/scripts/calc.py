#!/usr/bin/env python3
import ast
import operator
import sys

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](evaluate(node.left), evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](evaluate(node.operand))
    raise ValueError(f"unsupported expression element: {ast.dump(node)}")


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: calc.py '<expression>'", file=sys.stderr)
        sys.exit(2)
    tree = ast.parse(sys.argv[1], mode="eval")
    print(evaluate(tree))


if __name__ == "__main__":
    main()
