"""Run the Python chunks of a documentation page in order, without rendering it.

    uv run python tools/run_page.py docs/articles/convergence.qmd [--show]

A quick check while writing a page: chunks marked ``#| eval: false`` are skipped, the
others run in one namespace, and the first error stops the run with the chunk that
raised it. ``--show`` prints the text of each chunk's last expression.
"""

from __future__ import annotations

import ast
import re
import sys
import time
import traceback
from pathlib import Path


def main(argv: list[str]) -> int:
    show = "--show" in argv
    page = Path(next(a for a in argv if not a.startswith("--")))
    chunks = re.findall(r"^```\{python\}\n(.*?)^```\s*$", page.read_text(), flags=re.M | re.S)
    namespace: dict = {"__name__": "__main__"}
    for number, chunk in enumerate(chunks, 1):
        if re.search(r"^#\|\s*eval:\s*false", chunk, flags=re.M):
            continue
        code = "\n".join(line for line in chunk.split("\n") if not line.startswith("#|"))
        started = time.time()
        try:
            tree = ast.parse(code)
            last = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
            exec(compile(tree, f"{page.name}#{number}", "exec"), namespace)
            if last is not None:
                value = eval(compile(ast.Expression(last.value), f"{page.name}#{number}", "eval"), namespace)
                if show and value is not None:
                    text = value.interpret() if hasattr(value, "interpret") else repr(value)
                    print(f"--- chunk {number}:\n{text[:1500]}")
        except Exception:
            print(f"\nERROR in chunk {number} of {page}:\n{code}\n")
            traceback.print_exc()
            return 1
        print(f"chunk {number}: ok ({time.time() - started:.1f} s)", flush=True)
    print(f"{page}: {len(chunks)} chunks")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
