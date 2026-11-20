"""Test setup: where the data come from, and synthetic data with known answers.

Tests marked ``data`` read the project's published files. They use, in this order:
``<PREFIX>_DATA_DIR``; a checkout of the data repository next to this one (the folder
named like the repository in project.yaml); otherwise the network.
"""

import os
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_CFG = yaml.safe_load((_ROOT / "project.yaml").read_text())
_ENV = f"{_CFG['package'].upper()}_DATA_DIR"
_SIBLING = _ROOT.parent / _CFG["repository"].split("/")[-1]
if not os.environ.get(_ENV) and (_SIBLING / "geo" / "scales.yaml").is_file():
    os.environ[_ENV] = str(_SIBLING)
