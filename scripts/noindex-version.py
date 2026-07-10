#!/usr/bin/env python3
"""Add `noindex: true` to every .mdx in a docs version and its locale mirrors.

Used at release-cut time (VERSIONING.md step 4) to de-index the version that
just lost `default: true`. Idempotent — safe to re-run. Covers the English
tree (`mysql-8.4/<version>/`) and the ja/ko/zh mirrors.

Usage:
    python3 scripts/noindex-version.py 0.0.4 [--dry-run] [--repo PATH]
"""

import argparse
import sys
from pathlib import Path

LOCALES = ["", "ja", "ko", "zh"]  # "" = English tree at repo root


def version_dirs(repo: Path, version: str):
    for locale in LOCALES:
        base = repo / locale / "mysql-8.4" / version if locale else repo / "mysql-8.4" / version
        if base.is_dir():
            yield base


def has_noindex(front_lines):
    return any(line.split(":", 1)[0].strip() == "noindex" for line in front_lines)


def add_noindex(text: str):
    """Return (new_text, changed). Inserts noindex into existing frontmatter,
    or prepends a frontmatter block if none exists."""
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            front = text[4:end]
            front_lines = front.split("\n")
            if has_noindex(front_lines):
                return text, False
            new_front = "noindex: true\n" + front
            return "---\n" + new_front + text[end:], True
    # No parseable frontmatter — prepend one.
    return "---\nnoindex: true\n---\n\n" + text, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("version", help="version dir to noindex, e.g. 0.0.4")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo", default=None, help="repo root (default: script's parent)")
    args = ap.parse_args()

    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parent.parent

    dirs = list(version_dirs(repo, args.version))
    if not dirs:
        print(f"error: no version dirs found for {args.version} under {repo}", file=sys.stderr)
        return 1

    changed = skipped = 0
    for base in dirs:
        for mdx in sorted(base.rglob("*.mdx")):
            text = mdx.read_text(encoding="utf-8")
            new_text, did = add_noindex(text)
            rel = mdx.relative_to(repo)
            if did:
                changed += 1
                if args.dry_run:
                    print(f"[would edit] {rel}")
                else:
                    mdx.write_text(new_text, encoding="utf-8")
                    print(f"[noindex]    {rel}")
            else:
                skipped += 1

    verb = "would change" if args.dry_run else "changed"
    print(f"\n{verb} {changed} file(s), {skipped} already had noindex.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
