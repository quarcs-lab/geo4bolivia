"""Where published files are read from: a local checkout of the repository, or GitHub.

Inside a clone of the repository, files are read from disk. Anywhere else (an
installed package, Google Colab), they are fetched from the repository named in
``project.yaml`` at ``ref`` (a branch, tag or commit). Environment variables,
with the package name as prefix (e.g. ``GEO4BOLIVIA_``):

- ``<PREFIX>_DATA_DIR``: read from this checkout instead of searching for one
- ``<PREFIX>_REF``: default git ref for remote reads (else ``default_ref`` in project.yaml)
- ``<PREFIX>_BASE_URL``: read from a mirror; ``{ref}`` in it is replaced by the ref
"""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

import requests

from . import project
from .project import local_root  # noqa: F401  (re-exported: store.local_root)


def default_ref() -> str:
    return project.env("REF") or project.config().get("default_ref", "main")


def raw_url(path: str, ref: str | None = None) -> str:
    """Public URL of a repository file, e.g. ``raw_url("data/district/gdppc.csv")``."""
    repo = project.config()["repository"]
    base = project.env("BASE_URL") or f"https://raw.githubusercontent.com/{repo}/{{ref}}/"
    return base.replace("{ref}", ref or default_ref()).rstrip("/") + "/" + path


def repo_root() -> Path:
    """The local repository root; raises if not inside a checkout (needed for building)."""
    root = project.local_root()
    if root is None:
        raise RuntimeError(f"This needs a local checkout of {project.config()['repository']} "
                           f"(or {project.ENV_PREFIX}_DATA_DIR).")
    return root


@lru_cache(maxsize=64)
def _download(url: str) -> bytes:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    return response.content


def open_binary(path: str, ref: str | None = None) -> io.BytesIO:
    """Read a repository file into memory, locally when possible (downloads are cached per session)."""
    root = project.local_root()
    if root is not None and ref is None:
        return io.BytesIO((root / path).read_bytes())
    return io.BytesIO(_download(raw_url(path, ref)))


def source(path: str, ref: str | None = None) -> str:
    """A path or URL suitable for readers that accept either (e.g. geopandas)."""
    root = project.local_root()
    if root is not None and ref is None:
        return str(root / path)
    return raw_url(path, ref)
