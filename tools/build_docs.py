"""Build the documentation site: function reference, examples, notebooks, pages and LLM files.

    uv run python tools/build_docs.py            # everything, into docs/_site
    uv run python tools/build_docs.py --no-render   # all the generated sources, without rendering

Steps:

1. stand-in images for pictures that do not exist yet (``tools/build_images.py``);
2. a Jupyter kernel named after the package, bound to this environment;
3. the function reference with quartodoc (``docs/reference/``, generated, not committed);
4. an example on every reference page, from ``docs/examples/<function>.py``: the code is
   shown as a Colab user would paste it and run at build time to show its result;
5. a Colab notebook per article and per guide (``notebooks/``, committed);
6. ``docs/llms.txt`` (committed): the index that AI assistants read first;
7. ``quarto render docs``: pages are executed here and frozen (``docs/_freeze``, committed);
8. ``docs/_site/llms-full.txt``: every page, signature, docstring and example in one file.
"""

from __future__ import annotations

import importlib
import inspect
import json
import posixpath
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SITE = DOCS / "_site"
EXAMPLES = DOCS / "examples"
NOTEBOOKS = ROOT / "notebooks"
CONFIG = yaml.safe_load((ROOT / "project.yaml").read_text())
PACKAGE = CONFIG["package"]
QUARTO = yaml.safe_load((DOCS / "_quarto.yml").read_text())
BASE = QUARTO["website"]["site-url"].rstrip("/")
REPO = QUARTO["website"]["repo-url"].rstrip("/")
COLAB_EMPTY = "https://colab.research.google.com/notebooks/empty.ipynb"
COLAB = REPO.replace("https://github.com/", "https://colab.research.google.com/github/") + "/blob/main/notebooks"
# Pages that become notebooks: the guides and every article
NOTEBOOK_PAGES = ["get-started", "explore", "analyze"]


def run(*cmd: str) -> None:
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)


def sections() -> list[dict]:
    """The reference sections of _quarto.yml: title, desc, contents (function names)."""
    return QUARTO["quartodoc"]["sections"]


def public_functions() -> dict:
    module = importlib.import_module(PACKAGE)
    return {name: getattr(module, name) for name in module.__all__}


# --- examples on the reference pages -----------------------------------------------------------

def example(name: str) -> str | None:
    path = EXAMPLES / f"{name}.py"
    return path.read_text().strip() if path.exists() else None


def runnable(code: str) -> str:
    """The example as run for the page: no shell lines (``!pip install ...``), readings shown as Markdown."""
    code = "\n".join(line for line in code.split("\n") if not line.lstrip().startswith("!")).strip()
    if ".interpret()" in code:
        code = re.sub(r"print\((\w+(?:\.\w+)*\.interpret\(\))\)", r"display(Markdown(\1))", code)
        code = "from IPython.display import Markdown, display\n" + code
    return code


def enrich_reference() -> None:
    """Append its example to every reference page, shown as pasted in Colab and run for its result."""
    missing = []
    for name in public_functions():
        page = DOCS / "reference" / f"{name}.qmd"
        code = example(name)
        if not page.exists():
            raise SystemExit(f"quartodoc wrote no page for {name}: is it in a section of docs/_quarto.yml?")
        if code is None:
            missing.append(name)
            continue
        text = page.read_text().rstrip()
        text += f"""

## Example {{.doc-section .doc-section-example}}

```python
{code}
```

::: {{.g4-example-links}}
[Open a blank Colab notebook to run it]({COLAB_EMPTY})
:::

```{{python}}
#| echo: false
#| warning: false
{runnable(code)}
```
"""
        page.write_text(text + "\n")
    if missing:
        raise SystemExit(f"No example in docs/examples/ for: {', '.join(missing)}")


# --- notebooks from pages ------------------------------------------------------------------------

def page_to_notebook(page: Path, target: Path) -> None:
    """A .qmd page as a Colab notebook: its prose as Markdown cells, its Python chunks as code cells."""
    text = page.read_text()
    meta = {}
    if text.startswith("---"):
        _, front, text = text.split("---", 2)
        meta = yaml.safe_load(front) or {}
    link = f"{BASE}/{page.relative_to(DOCS).with_suffix('.html').as_posix()}"
    folder = page.parent.relative_to(DOCS).as_posix().strip(".")
    cells = [{"cell_type": "markdown", "metadata": {}, "source": (
        f"# {meta.get('title', page.stem)}\n\n"
        f"This notebook is the page [{meta.get('title', page.stem)}]({link}) of the "
        f"[{PACKAGE} documentation]({BASE}/). Run the cells from the top.")}]
    chunk = re.compile(r"^```\{python\}\n(.*?)^```\s*$", flags=re.M | re.S)
    position = 0
    for match in chunk.finditer(text):
        prose = clean_prose(text[position:match.start()], folder)
        if prose:
            cells.append({"cell_type": "markdown", "metadata": {}, "source": prose})
        code = "\n".join(line for line in match.group(1).split("\n") if not line.startswith("#|")).strip()
        if code:
            cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": code})
        position = match.end()
    prose = clean_prose(text[position:], folder)
    if prose:
        cells.append({"cell_type": "markdown", "metadata": {}, "source": prose})
    notebook = {"cells": cells, "nbformat": 4, "nbformat_minor": 5,
                "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                             "language_info": {"name": "python"}}}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n")


def clean_prose(text: str, folder: str = "") -> str:
    """Page prose as notebook Markdown: no raw HTML blocks or Quarto divs, links made absolute.

    ``folder`` is the page's folder inside the site (``""`` or ``"articles"``), from which its relative links resolve.
    """
    text = re.sub(r"^```\{=html\}\n.*?^```\s*$", "", text, flags=re.M | re.S)
    text = re.sub(r"^:::+.*$", "", text, flags=re.M)
    def absolute(match: re.Match) -> str:
        target = posixpath.normpath(posixpath.join(folder, match.group(1)))
        return f"]({BASE}/{target}.html{match.group(2) or ''})"

    text = re.sub(r"\]\((?!https?://|#|mailto:)([^)]+?)\.qmd(#[^)]*)?\)", absolute, text)
    text = re.sub(r"\{[.#][^}\n]*\}", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def build_notebooks() -> None:
    pages = [DOCS / f"{name}.qmd" for name in NOTEBOOK_PAGES]
    pages += sorted(p for p in (DOCS / "articles").glob("*.qmd") if p.stem != "index")
    for page in pages:
        if page.exists():
            page_to_notebook(page, NOTEBOOKS / f"{page.stem}.ipynb")
    print(f"notebooks: {len(list(NOTEBOOKS.glob('*.ipynb')))} in {NOTEBOOKS.relative_to(ROOT)}/")


# --- files for AI assistants ---------------------------------------------------------------------

def signature(name: str, obj) -> str:
    try:
        return f"geo.{name}{inspect.signature(obj)}"
    except (TypeError, ValueError):
        return f"geo.{name}(...)"


def first_line(obj) -> str:
    return (inspect.getdoc(obj) or "").split("\n")[0]


def page_titles() -> list[tuple[str, str, str]]:
    """(title, path, description) of every page of the site that has a source."""
    out = []
    for page in [*sorted(DOCS.glob("*.qmd")), *sorted((DOCS / "articles").glob("*.qmd"))]:
        text = page.read_text()
        meta = yaml.safe_load(text.split("---", 2)[1]) if text.startswith("---") else {}
        if page.stem == "index" and page.parent == DOCS:
            continue
        out.append((meta.get("title", page.stem), page.relative_to(DOCS).with_suffix(".html").as_posix(),
                    meta.get("description", "")))
    return out


def build_llms(full: bool) -> None:
    functions = public_functions()
    lines = [f"# {PACKAGE}", "",
             f"> {QUARTO['website']['description']}", "",
             f"{PACKAGE} is the Python package of the {CONFIG['name']}. It reads the observatory's published data "
             f"(https://github.com/{CONFIG['repository']}) and runs the fundamental analyses of spatial data science "
             "on them. Install with `pip install " + PACKAGE + "` and `import " + PACKAGE + " as geo`. "
             "Every analysis function takes a dataset id or a panel with `geo_id` and `year`, finds boundaries, "
             "weights and labels itself, and returns a result object with `.df`, `.fig` (Plotly), `.gt` (table) and "
             "`.interpret()`.", "",
             "## Pages", ""]
    lines += [f"- [{title}]({BASE}/{path})" + (f": {desc}" if desc else "") for title, path, desc in page_titles()]
    lines += [f"- [Function reference]({BASE}/reference/index.html): every public function, with an example",
              f"- [llms-full.txt]({BASE}/llms-full.txt): all of the above in one file", ""]
    for section in sections():
        lines += [f"## {section['title']}", ""]
        for name in section["contents"]:
            lines.append(f"- [`{signature(name, functions[name])}`]({BASE}/reference/{name}.html): {first_line(functions[name])}")
        lines.append("")
    (DOCS / "llms.txt").write_text("\n".join(lines).rstrip() + "\n")
    print("docs/llms.txt")
    if not full:
        return
    parts = ["\n".join(lines)]
    for title, path, _ in page_titles():
        source = DOCS / Path(path).with_suffix(".qmd")
        parts.append(f"\n\n{'=' * 100}\n# {title} ({BASE}/{path})\n{'=' * 100}\n\n{source.read_text()}")
    parts.append(f"\n\n{'=' * 100}\n# Function reference\n{'=' * 100}\n")
    for name, obj in functions.items():
        parts.append(f"\n## {signature(name, obj)}\n\n{inspect.getdoc(obj) or ''}\n")
        if example(name):
            parts.append(f"Example:\n\n```python\n{example(name)}\n```\n")
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "llms-full.txt").write_text("".join(parts))
    print("docs/_site/llms-full.txt")


# --- main ------------------------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if "--llms" in argv:
        build_llms(full=False)
        return 0
    if not (DOCS / "images" / "hero.webp").exists() or "--placeholders" in argv:
        run(sys.executable, "tools/build_images.py", "--placeholders")
    run(sys.executable, "-m", "ipykernel", "install", "--user", "--name", PACKAGE,
        "--display-name", f"Python ({PACKAGE} docs)")
    run(sys.executable, "-m", "quartodoc", "build", "--config", "docs/_quarto.yml")
    enrich_reference()
    build_notebooks()
    build_llms(full=False)
    if "--no-render" in argv:
        return 0
    run("quarto", "render", "docs")
    build_llms(full=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
