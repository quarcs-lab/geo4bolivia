"""Command line: ``geo4bolivia build``, ``geo4bolivia validate``, ``geo4bolivia list``."""

from __future__ import annotations

import argparse
import sys

from .project import PACKAGE, config


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog=PACKAGE, description=f"{config()['name']}: data tools")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="regenerate published files from raw/ (all, geo, or one dataset)")
    b.add_argument("target", nargs="?", default="all")
    v = sub.add_parser("validate", help="check geo/ and the datasets (all, or one dataset)")
    v.add_argument("dataset", nargs="?")
    sub.add_parser("list", help="list datasets, scales and years")
    args = parser.parse_args(argv)

    if args.command == "build":
        from .build import build
        build(args.target)
        return 0
    if args.command == "validate":
        from .validate import run
        reports = run(args.dataset)
        for r in reports:
            print(r)
        failed = [r for r in reports if not r.ok]
        print(f"\n{len(reports) - len(failed)}/{len(reports)} passed")
        return 1 if failed else 0
    if args.command == "list":
        from .io import datasets
        print(datasets().drop(columns=["parquet"]).to_string(index=False))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
