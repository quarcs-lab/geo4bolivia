"""The documentation covers the public functions: a reference section and an example for each."""

from pathlib import Path

import pytest
import yaml

import geo4bolivia as geo

DOCS = Path(__file__).resolve().parents[1] / "docs"
pytestmark = pytest.mark.skipif(not (DOCS / "_quarto.yml").exists(), reason="no documentation site in this project")


def test_every_public_function_is_in_the_reference_once():
    sections = yaml.safe_load((DOCS / "_quarto.yml").read_text())["quartodoc"]["sections"]
    listed = [name for section in sections for name in section["contents"]]
    assert sorted(listed) == sorted(geo.__all__), set(listed) ^ set(geo.__all__)
    assert len(listed) == len(set(listed))


def test_every_public_function_has_an_example_and_a_documented_return():
    for name in geo.__all__:
        example = DOCS / "examples" / f"{name}.py"
        assert example.exists(), f"no docs/examples/{name}.py"
        code = example.read_text()
        assert code.startswith("!pip install -q "), f"{example.name} must start with its install line"
        assert f"geo.{name}(" in code or f".{name}(" in code, f"{example.name} does not call {name}"
        doc = getattr(geo, name).__doc__ or ""
        assert doc.strip(), f"{name} has no docstring"
        assert "Examples\n" not in doc, f"{name}: examples live in docs/examples/, not in the docstring"


def test_examples_fit_the_code_box():
    for example in (DOCS / "examples").glob("*.py"):
        long = [line for line in example.read_text().split("\n") if len(line) > 88]
        assert not long, f"{example.name}: {long[0]!r}"
