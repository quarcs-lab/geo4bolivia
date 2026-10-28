"""Project identity, read from ``project.yaml``.

Nothing else in the package hard-codes the project: the package name comes from
the folder this module lives in, and the repository, country code and
projection come from ``project.yaml``. Inside a checkout that file is read from
the repository root; an installed package reads the copy bundled with it.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

PACKAGE = __name__.split(".")[0]          # "geo4bolivia" (the folder name in src/)
ENV_PREFIX = PACKAGE.upper()              # GEO4BOLIVIA_DATA_DIR, ..._BASE_URL, ..._REF
CONFIG_FILE = "project.yaml"
_BUNDLED = Path(__file__).resolve().parent / CONFIG_FILE


def env(name: str) -> str | None:
    """An environment setting for this project, e.g. ``env("DATA_DIR")``."""
    return os.environ.get(f"{ENV_PREFIX}_{name}")


def _is_root(path: Path) -> bool:
    """A checkout of *this* project: has geo/scales.yaml and a project.yaml naming this package."""
    cfg = path / CONFIG_FILE
    if not (cfg.is_file() and (path / "geo" / "scales.yaml").is_file()):
        return False
    try:
        return (yaml.safe_load(cfg.read_text()) or {}).get("package") == PACKAGE
    except yaml.YAMLError:
        return False


@lru_cache(maxsize=1)
def local_root() -> Path | None:
    """The repository root if running inside a checkout (or ``<PREFIX>_DATA_DIR``), else ``None``."""
    explicit = env("DATA_DIR")
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not _is_root(root):
            raise FileNotFoundError(f"{ENV_PREFIX}_DATA_DIR={explicit} has no {CONFIG_FILE} for package {PACKAGE!r}")
        return root
    for path in [Path.cwd(), *Path.cwd().parents, *Path(__file__).resolve().parents]:
        if _is_root(path):
            return path
    return None


@lru_cache(maxsize=1)
def config() -> dict:
    """The contents of project.yaml."""
    root = local_root()
    path = root / CONFIG_FILE if root is not None else _BUNDLED
    if not path.is_file():
        raise FileNotFoundError(f"{CONFIG_FILE} not found (looked in {path})")
    return yaml.safe_load(path.read_text())


def country_code() -> str:
    return config()["country"]["iso2"]


def equal_area_crs() -> str:
    return config().get("equal_area_crs", "EPSG:6933")
