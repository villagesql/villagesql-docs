#!/usr/bin/env python3
"""Re-run the SQL examples in the guides that carry captured output.

The tutorial has verify-tutorial-examples.py. The guides had nothing, which is
how a `CREATE INDEX` statement came to be published with an `EXPLAIN` plan under
it as though that were its output. This covers the guides listed in GUIDES
below, and it is meant to grow one guide at a time as each is checked by hand
once.

A guide is read top to bottom in 1 session, the way a reader works through it.
Every ```sql block runs. A block followed by a ```text block is compared with
what the server printed; a block with no ```text block after it is setup, and
only has to succeed.

Plans are compared by shape, not by number. `EXPLAIN` prints costs and row
estimates that come from InnoDB's sampled statistics, so they differ between
machines and even between runs; the guides say so themselves. Every
`cost=`, `rows=` and timing is removed before the comparison, and what is left
has to appear in the live output line for line.

    VSQL_CLIENT=/path/to/mysql VSQL_SOCKET=/tmp/mysql.sock \
        python3 scripts/verify-guide-examples.py

Exits non-zero when any example disagrees with the page.
"""

import importlib.util, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "tutorial_verifier", os.path.join(REPO, "scripts",
                                      "verify-tutorial-examples.py"))
tv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tv)

# Each guide names the database its statements run in, and the tables it creates
# for itself. The tables are dropped before and after the run, so a crashed run
# cannot leave one behind in a database other pages describe.
GUIDES = {
    "guides/joins.mdx": {
        "db": "guides_joins_scratch",
        "own_tables": ["orders", "customers"],
        "scratch": True,
    },
    "guides/group-by-having.mdx": {
        "db": "sakila",
        "own_tables": [],
        "scratch": False,
    },
    "guides/ctes-in-mysql.mdx": {
        "db": "sakila",
        "own_tables": ["employees"],
        "scratch": False,
    },
}

# A cost or row estimate in brackets, in any of the forms EXPLAIN prints:
# (cost=103 rows=1000), (cost=2.5..2.5 rows=0), (rows=4). A bracket without
# rows= in it, such as (films=a.films), is part of the plan and is kept.
NOISE = re.compile(r"\s*\((?:cost=[\d.e+-]+(?:\.\.[\d.e+-]+)?\s*)?rows=[\d.e+-]+\)"
                   r"|\s*\(\d+\.\d+ sec\)")
ROW_HEADER = re.compile(r"^\*{5,}.*row.*\*{5,}$")
G_LABEL = re.compile(r"^\s*[A-Za-z_]+: ")


def shape(block):
    """A plan or result with the machine-specific parts taken out.

    The indentation of a tree plan carries its nesting, so a line beginning with
    -> keeps its leading spaces. A \\G label line is padded to the width of the
    widest label, which changes when a page quotes only some of the fields, so
    those are compared without their padding.
    """
    out = []
    for line in block.strip().split("\n"):
        line = line.rstrip()
        if ROW_HEADER.match(line.strip()):
            continue
        if line.lstrip().startswith("EXPLAIN: "):
            line = line.lstrip()[len("EXPLAIN: "):]
        line = NOISE.sub("", line).rstrip()
        if G_LABEL.match(line):
            line = line.strip()
        if line:
            out.append(line)
    return out


def sql_blocks(text):
    """Every ```sql block in page order, with its ```text output when it has one."""
    fences, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        if lines[i].startswith("```"):
            lang = lines[i][3:].strip()
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            fences.append((lang, "\n".join(lines[i + 1:j])))
            i = j + 1
        else:
            i += 1
    out = []
    for k, (lang, body) in enumerate(fences):
        if lang != "sql":
            continue
        nxt = fences[k + 1] if k + 1 < len(fences) else None
        out.append((body.strip(), nxt[1] if nxt and nxt[0] == "text" else None))
    return out


def drop_own(db, tables):
    for t in tables:
        tv.run(f"DROP TABLE IF EXISTS {t};", db=db)


def main():
    ok = bad = setup = 0
    for rel, cfg in GUIDES.items():
        path = os.path.join(REPO, rel)
        db = cfg["db"]
        if cfg["scratch"]:
            tv.run(f"DROP DATABASE IF EXISTS {db};", db="mysql")
            tv.run(f"CREATE DATABASE {db};", db="mysql")
        else:
            drop_own(db, cfg["own_tables"])
        try:
            for sql, shown in sql_blocks(open(path).read()):
                if shown is None:
                    tv.run(sql, db=db)
                    setup += 1
                    continue
                live = (tv.printed_session(tv.run(sql, db=db), sql)
                        if tv.is_multi(sql)
                        else tv.printed(tv.run(sql, db=db), sql))
                want, got = shape(shown), shape(live)
                missing = [l for l in want if l not in got]
                if not missing:
                    ok += 1
                    continue
                bad += 1
                print(f"MISMATCH {rel}: {sql.splitlines()[0][:60]}")
                for line in missing:
                    print(f"   the server did not print: {line}")
                print("   live output was:")
                for line in got:
                    print(f"     {line}")
        finally:
            if cfg["scratch"]:
                tv.run(f"DROP DATABASE IF EXISTS {db};", db="mysql")
            else:
                drop_own(db, cfg["own_tables"])
    print(f"\nmatched {ok}, mismatched {bad}, setup statements {setup}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
