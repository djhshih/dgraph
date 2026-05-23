#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dgraph.dot import dot_to_source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Python decision-graph source from a DOT file.",
    )
    parser.add_argument("input", help="Path to input DOT file")
    parser.add_argument(
        "-o",
        "--output",
        help="Path to output Python file. Defaults to stdout.",
    )
    parser.add_argument(
        "--graph-var",
        default="graph",
        help="Name of the generated graph variable (default: graph)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    try:
        dot_text = input_path.read_text()
    except OSError as exc:
        parser.error(f"could not read {input_path}: {exc}")

    source = dot_to_source(dot_text, graph_var=args.graph_var)

    if args.output:
        output_path = Path(args.output)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(source)
        except OSError as exc:
            parser.error(f"could not write {output_path}: {exc}")
    else:
        sys.stdout.write(source)
        if not source.endswith("\n"):
            sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
