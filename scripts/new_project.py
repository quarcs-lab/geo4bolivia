"""Start a new geo4<country> project from this repository (see TEMPLATE.md).

Copies the generic parts (Python package, tests, guides), renames the package,
writes a fresh project.yaml, scales.yaml, README.md and CLAUDE.md, and leaves out
everything that belongs to this project: raw inputs, published data, metadata,
notebooks and the website.

Example:

    python scripts/new_project.py ../geo4laos --package geo4laos --country Laos \\
        --iso2 LA --iso3 LAO --repo my-org/geo4laos

Only the Python standard library is needed.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from string import Template
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
TEMPLATES = HERE / "scripts" / "template"

# Generic files, copied as they are (with the package and repository renamed)
GENERIC = [
    ".gitignore", "jupytext.toml", "CONTRIBUTING_DATA.md", "TEMPLATE.md", ".github/workflows/release.yml",
    "docs/data-infrastructure.md", "docs/publishing.md",
    "scripts/new_project.py", "scripts/template",
    "tests/test_core.py",
]
CORE_MODULES = ["__init__.py", "aggregate.py", "bridge.py", "cli.py", "create.py", "io.py", "metadata.py",
                "project.py", "scales.py", "store.py", "validate.py"]
BUILD_MODULES = ["common.py", "gadm.py", "_template.py", "_geo_template.py"]


BUILD_INIT = '''"""Builders that regenerate every published file from ``raw/``.

``geo`` must run first: dataset builders take their geo IDs from geo/units.
Register each new dataset builder in DATASETS (see CONTRIBUTING_DATA.md).
"""

from . import geo
from .common import write_catalog

DATASETS = {}   # e.g. {"gdppc": gdppc.build} after `from . import gdppc`


def build(target: str = "all") -> None:
    if target in ("all", "geo"):
        print("geo")
        geo.build()
    for name, builder in DATASETS.items():
        if target in ("all", name):
            print(name)
            builder()
    if target not in ("all", "geo", *DATASETS):
        raise SystemExit(f"Unknown build target {target!r}; use all, geo or one of {', '.join(DATASETS)}")
    print("catalog")
    write_catalog()
'''


def read_project() -> dict:
    """The few project.yaml values the script needs, without a YAML library."""
    text = (HERE / "project.yaml").read_text()
    def get(key: str) -> str:
        return re.search(rf"^{key}:\s*(\S+)", text, re.M).group(1)
    return {"package": get("package"), "repository": get("repository"), "website": get("website")}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dest", help="folder for the new project (must not exist or be empty)")
    p.add_argument("--package", required=True, help="Python package / PyPI name, e.g. geo4laos")
    p.add_argument("--country", required=True, help="country name, e.g. Laos")
    p.add_argument("--iso2", required=True, help="ISO 3166-1 alpha-2 code: the prefix of every geo_id, e.g. LA")
    p.add_argument("--iso3", required=True, help="ISO 3166-1 alpha-3 code used by GADM, e.g. LAO")
    p.add_argument("--repo", required=True, help="GitHub repository owner/name, e.g. my-org/geo4laos")
    p.add_argument("--name", help="project name (default: GeoDevelopment Observatory of <country>)")
    p.add_argument("--short-name", help="short name (default: GDO-<country>)")
    p.add_argument("--website", help="website URL (default: GitHub Pages of the repository)")
    p.add_argument("--levels", default="province,district",
                   help="comma-separated scale ids for GADM levels 1, 2, ... (default: province,district)")
    args = p.parse_args(argv)

    if not re.fullmatch(r"[a-z][a-z0-9_]*", args.package):
        p.error("--package must be a valid Python name in lowercase, e.g. geo4laos")
    dest = Path(args.dest).resolve()
    if dest.exists() and any(dest.iterdir()):
        p.error(f"{dest} exists and is not empty")
    old = read_project()
    owner, repo_name = args.repo.split("/")
    new = {
        "package": args.package, "repository": args.repo, "country": args.country,
        "iso2": args.iso2.upper(), "iso3": args.iso3.upper(),
        "name": args.name or f"GeoDevelopment Observatory of {args.country}",
        "short_name": args.short_name or f"GDO-{args.country.replace(' ', '')}",
        "website": args.website or f"https://{owner.lower()}.github.io/{repo_name}/",
    }
    levels = [s.strip() for s in args.levels.split(",") if s.strip()]

    def rename(text: str) -> str:
        text = text.replace(old["repository"], new["repository"]).replace(old["website"], new["website"])
        return text.replace(old["package"], new["package"]).replace(old["package"].upper(), new["package"].upper())

    def copy(src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in {".py", ".md", ".toml", ".yaml", ".yml", ".txt", ".json", ""} or src.name.startswith("."):
            dst.write_text(rename(src.read_text()))
        else:
            shutil.copy2(src, dst)

    # 1. generic files
    for rel in GENERIC:
        src = HERE / rel
        files = [f for f in src.rglob("*") if f.is_file() and "__pycache__" not in f.parts] if src.is_dir() else [src]
        for f in files:
            copy(f, dest / f.relative_to(HERE))
    pkg_src, pkg_dst = HERE / "src" / old["package"], dest / "src" / new["package"]
    for m in CORE_MODULES:
        copy(pkg_src / m, pkg_dst / m)
    for m in BUILD_MODULES:
        copy(pkg_src / "build" / m, pkg_dst / "build" / m)
    geo_builder = (pkg_dst / "build" / "_geo_template.py").read_text()
    geo_builder = geo_builder.replace("gadm41_XXX_2.json", f"gadm41_{new['iso3']}_{len(levels)}.json")
    geo_builder = geo_builder.replace('{1: "province", 2: "district"}',
                                      "{" + ", ".join(f'{i}: "{s}"' for i, s in enumerate(levels, 1)) + "}")
    (pkg_dst / "build" / "geo.py").write_text(geo_builder)
    (pkg_dst / "__init__.py").write_text(re.sub(r'__version__ = ".*"', '__version__ = "0.1.0"',
                                                (pkg_dst / "__init__.py").read_text()))

    # 2. files generated from templates
    values = dict(new, package_upper=new["package"].upper(), levels=", ".join(levels),
                  finest=levels[-1], coarsest=levels[0], n_levels=len(levels))
    for tpl in sorted(TEMPLATES.glob("*.tpl")):          # "docs__x.md.tpl" -> docs/x.md
        out = dest / tpl.name.removesuffix(".tpl").replace("__", "/")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(Template(tpl.read_text()).substitute(values))
    (pkg_dst / "build" / "__init__.py").write_text(BUILD_INIT)
    scales = [f"# Spatial scales of the {new['name']}. See docs/data-infrastructure.md.\n",
              "country:\n  label: Country\n  kind: admin\n  level: 0\n  parent: null\n"
              f"  id_pattern: '^{new['iso2']}$'\n  example: {new['iso2']}\n  source: GADM 4.1 (dissolved)\n  status: active\n"]
    parent, pattern = "country", new["iso2"]
    for i, s in enumerate(levels + ["subdistrict"], 1):
        pattern += r"-\d{2}"
        example = new["iso2"] + "-01" * i
        status = "active" if i <= len(levels) else "planned"
        scales.append(f"\n{s}:\n  label: {s.replace('_', ' ').capitalize()}\n  kind: admin\n  level: {i}\n"
                      f"  parent: {parent}\n  id_pattern: '^{pattern}$'\n  example: {example}\n  digits: 2\n"
                      f"  source: GADM 4.1 level {i}\n  status: {status}\n")
        parent = s
    scales.append(f"\ngrid10k:\n  label: 10 km grid cell\n  kind: grid\n  level: null\n  parent: null\n"
                  f"  id_pattern: '^{new['iso2']}-G10K-r\\d{{3}}c\\d{{3}}$'\n  example: {new['iso2']}-G10K-r012c034\n"
                  f"  cell_size_m: 10000\n  source: Regular grid in an equal-area projection\n  status: planned\n")
    (dest / "geo").mkdir(parents=True, exist_ok=True)
    (dest / "geo/scales.yaml").write_text("".join(scales))
    (dest / "metadata").mkdir(exist_ok=True)
    (dest / "metadata/index.json").write_text('{\n  "datasets": []\n}\n')
    for folder in ("raw/boundaries", "data", "docs/datasets", "notebooks"):
        (dest / folder).mkdir(parents=True, exist_ok=True)

    # 3. pyproject: same dependencies and settings, new identity
    py = rename((HERE / "pyproject.toml").read_text())
    py = re.sub(r'version = ".*?"', 'version = "0.1.0"', py, count=1)
    py = re.sub(r'description = ".*?"', f'description = "Subnational development data for {args.country} '
                f'across spatial scales ({new["name"]})"', py, count=1)
    py = re.sub(r'keywords = \[.*?\]', f'keywords = ["{args.country.lower()}", "geospatial", "regional development", '
                '"subnational data", "panel data", "gadm"]', py, count=1)
    (dest / "pyproject.toml").write_text(py)
    shutil.copy2(HERE / "LICENSE", dest / "LICENSE")

    print(f"Created {new['name']} in {dest}\n")
    print("Next steps (also in TEMPLATE.md):")
    print(f"  cd {dest}")
    print(f"  git init && git add -A && git commit -m 'Start from the {old['package']} template'")
    print(f"  # put the GADM level-{len(levels)} file at raw/boundaries/gadm41_{new['iso3']}_{len(levels)}.json")
    print(f"  uv sync && uv run {new['package']} build && uv run {new['package']} validate && uv run pytest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
