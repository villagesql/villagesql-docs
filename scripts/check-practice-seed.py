#!/usr/bin/env python3
"""Check that the practice database is defined once, in 2 places that agree.

scripts/tutorial-practice.sql is what verify-tutorial-examples.py loads before
a lesson that changes data. tutorial/insert.mdx prints the same statements for
the reader to run. A reader whose tables differ from the ones the examples were
captured against gets different output and no explanation, so the 2 copies have
to stay byte for byte the same.

Exits non-zero and prints a diff when they drift.
"""

import difflib, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "tutorial-practice.sql")
PAGE = os.path.join(REPO, "tutorial", "insert.mdx")
START = "DROP DATABASE IF EXISTS sakila_practice;"


def main():
    script = open(SCRIPT).read()
    if START not in script:
        print(f"{SCRIPT} no longer starts the seed with {START!r}")
        return 1
    seed = script[script.index(START):].strip()

    block = re.search(r"```sql\n(" + re.escape(START) + r".*?)```",
                      open(PAGE).read(), re.S)
    if not block:
        print(f"{PAGE} has no sql block beginning {START!r}")
        return 1
    shown = block.group(1).strip()

    if seed == shown:
        return 0
    print("The practice seed and the block in tutorial/insert.mdx disagree:")
    for line in difflib.unified_diff(seed.split("\n"), shown.split("\n"),
                                     "scripts/tutorial-practice.sql",
                                     "tutorial/insert.mdx", lineterm=""):
        print(line)
    return 1


if __name__ == "__main__":
    sys.exit(main())
