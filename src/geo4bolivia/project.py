"""Project identity, read from ``project.yaml``.

Nothing else in the package hard-codes the project: the package name comes from
the folder this module lives in, and the data repository, country code and
projection come from ``project.yaml``. The package carries its own copy (bundled
into the wheel; at the repository root in a source checkout). Inside a checkout of
the data repository, that repository's ``project.yaml`` is read on top of it.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

PACKAGE = __name__.split(".")[0]          # "geo4bolivia" (the folder name in src/)
ENV_PREFIX = PACKAGE.upper()              # GEO4BOLIVIA_DATA_DIR, ..._BASE_URL, ..._REF
CONFIG_FILE = "project.yaml"
_BUNDLED = Path(__file__).resolve().parent / CONFIG_FILE          # in an installed wheel
_SOURCE = Path(__file__).resolve().parents[2] / CONFIG_FILE       # in a source checkout of the package


def env(name: str) -> str | None:
    """An environment setting for this project, e.g. ``env("DATA_DIR")``."""
    return os.environ.get(f"{ENV_PREFIX}_{name}")


def _is_root(path: Path) -> bool:
    """A checkout of this project's data repository: geo/scales.yaml and a project.yaml naming this package."""
    cfg = path / CONFIG_FILE
    if not (cfg.is_file() and (path / "geo" / "scales.yaml").is_file()):
        return False
    try:
        return (yaml.safe_load(cfg.read_text()) or {}).get("package") == PACKAGE
    except yaml.YAMLError:
        return False


@lru_cache(maxsize=1)
def local_root() -> Path | None:
    """The data repository's root if running inside a checkout of it (or ``<PREFIX>_DATA_DIR``), else ``None``."""
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


def _own_config() -> dict:
    """The package's own project.yaml."""
    for path in (_BUNDLED, _SOURCE):
        if path.is_file():
            cfg = yaml.safe_load(path.read_text()) or {}
            if cfg.get("package") == PACKAGE:
                return cfg
    raise FileNotFoundError(f"{CONFIG_FILE} not found (looked in {_BUNDLED} and {_SOURCE})")


@lru_cache(maxsize=1)
def config() -> dict:
    """The project settings: the package's project.yaml, with the data repository's on top inside a checkout."""
    root = local_root()
    if root is None:
        return _own_config()
    local = yaml.safe_load((root / CONFIG_FILE).read_text()) or {}
    try:
        return {**_own_config(), **local}
    except FileNotFoundError:
        return local


def country_code() -> str:
    return config()["country"]["iso2"]


def equal_area_crs() -> str:
    return config().get("equal_area_crs", "EPSG:6933")
