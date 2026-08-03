#!/usr/bin/env python3
"""Stamp `canonical` frontmatter on dev pages so search engines consolidate
ranking onto the equivalent stable page.

Rule: a dev page gets `canonical: <stable-url>` only when a same-slug page
exists under stable/. A dev-only page (no stable equivalent) is left alone so
it self-canonicals and ranks on its own. Archives are intentionally NOT stamped:
they carry `noindex`, and noindex + canonical are contradictory signals.

Idempotent: re-running replaces an existing canonical line rather than
duplicating it. Called from the release shuffle after promoting dev.

Usage:
    python3 scripts/stamp-canonicals.py [--dry-run] [--repo PATH]
"""

import argparse
import sys
from pathlib import Path

BASE = "https://villagesql.com/docs"

# (dev dir relative to repo root, stable dir, url path prefix for the stable slot)
PAIRS = [
    ("mysql-8.4/dev", "mysql-8.4/stable", "mysql-8.4/stable"),
]


def set_canonical(path: Path, url: str, dry_run: bool) -> str:
    lines = path.read_text(encoding="utf-8").split("\n")
    if not lines or lines[0].strip() != "---":
        return "skip-no-frontmatter"
    try:
        close = lines.index("---", 1)
    except ValueError:
        return "skip-unterminated-frontmatter"
    new_line = f'canonical: "{url}"'
    for i in range(1, close):
        if lines[i].startswith("canonical:"):
            if lines[i] == new_line:
                return "unchanged"
            if not dry_run:
                lines[i] = new_line
                path.write_text("\n".join(lines), encoding="utf-8")
            return "would-update" if dry_run else "updated"
    if not dry_run:
        lines.insert(1, new_line)
        path.write_text("\n".join(lines), encoding="utf-8")
    return "would-add" if dry_run else "added"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo", default=None, help="repo root (default: script's parent)")
    args = ap.parse_args()

    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parent.parent

    counts = {}
    for dev_rel, stable_rel, prefix in PAIRS:
        dev_dir = repo / dev_rel
        stable_dir = repo / stable_rel
        if not dev_dir.is_dir():
            print(f"error: dev dir missing: {dev_rel}", file=sys.stderr)
            return 1
        for p in sorted(dev_dir.rglob("*.mdx")):
            slug = str(p.relative_to(dev_dir)).removesuffix(".mdx")
            if not (stable_dir / f"{slug}.mdx").exists():
                counts["dev-only-skipped"] = counts.get("dev-only-skipped", 0) + 1
                continue
            r = set_canonical(p, f"{BASE}/{prefix}/{slug}", args.dry_run)
            counts[r] = counts.get(r, 0) + 1

    for k in sorted(counts):
        print(f"  {k}: {counts[k]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
