"""Command line: ``build``, ``validate``, ``list``, ``search <words>`` and ``info <dataset>``."""

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
    s = sub.add_parser("search", help="find variables whose name, label or description match the words")
    s.add_argument("words", nargs="+")
    i = sub.add_parser("info", help="describe a dataset: coverage, sources, licenses, citation")
    i.add_argument("dataset")
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
        print(datasets()[["dataset", "scale", "years", "units", "variables", "title"]].to_string(index=False))
        return 0
    if args.command == "search":
        from .discover import search
        found = search(" ".join(args.words))
        print(found.drop(columns="description").to_string(index=False) if len(found) else "No variable matches.")
        return 0
    if args.command == "info":
        from .discover import info
        print(info(args.dataset))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
