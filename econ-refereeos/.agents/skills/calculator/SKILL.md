---
name: calculator
description: Evaluate arithmetic expressions using a sandboxed Python script.
version: 0.1.0
---

# Calculator

Use this skill whenever the user asks for an arithmetic calculation
(addition, subtraction, multiplication, division, exponentiation, modulo,
or any expression that combines them).

## How to use

Call the `run_skill_script` tool with:

- `name`: `"calculator"`
- `script`: `"calc.py"`
- `args`: a single-element list containing the expression as a string,
  e.g. `["(2 + 3) * 4"]`.

The script prints the result of the expression. Report the printed value
back to the user verbatim.

## Examples

- "What's 17 * 23?" → `args=["17 * 23"]`
- "Compute (100 - 7) / 3" → `args=["(100 - 7) / 3"]`
