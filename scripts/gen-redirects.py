#!/usr/bin/env python3
"""Generate the docs.json redirect block for a retired dev version.

Used at release-cut time (VERSIONING.md step 6). Mirrors the existing
`0.0.4-dev` -> `0.0.4` pattern: one bare-root entry plus one entry per page.
Enumerates pages from the on-disk version dir so the list is always complete.

Usage:
    python3 scripts/gen-redirects.py 0.0.5-dev 0.0.5 [--repo PATH] [--source-dir DIR]

Paste the output immediately after the opening `"redirects": [` line in
docs.json (leading position avoids any trailing-comma issue).
"""

import argparse
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old", help="retired version, e.g. 0.0.5-dev")
    ap.add_argument("new", help="new stable version, e.g. 0.0.5")
    ap.add_argument("--repo", default=None, help="repo root (default: script's parent)")
    ap.add_argument("--source-dir", default=None,
                    help="version dir to read page list from "
                         "(default: mysql-8.4/<old>, falling back to <new>)")
    args = ap.parse_args()

    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parent.parent

    if args.source_dir:
        src = Path(args.source_dir)
    else:
        src = repo / "mysql-8.4" / args.old
        if not src.is_dir():
            src = repo / "mysql-8.4" / args.new

    if not src.is_dir():
        print(f"error: source dir not found: {src}", file=sys.stderr)
        return 1

    pages = sorted(p.relative_to(src).with_suffix("").as_posix() for p in src.rglob("*.mdx"))

    entries = [(f"/mysql-8.4/{args.old}", f"/mysql-8.4/{args.new}")]
    entries += [(f"/mysql-8.4/{args.old}/{p}", f"/mysql-8.4/{args.new}/{p}") for p in pages]

    blocks = []
    for source, dest in entries:
        blocks.append(
            "    {\n"
            f'      "source": "{source}",\n'
            f'      "destination": "{dest}"\n'
            "    },"
        )
    print("\n".join(blocks))
    print(f"\n// {len(entries)} redirect entries generated", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
