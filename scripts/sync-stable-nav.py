#!/usr/bin/env python3
"""Rebuild one product's stable navigation from its dev navigation.

promote-release.py copies the dev pages into the stable slot, but the stable
menus in docs.json are separate lists, so a page that is new in dev would be
on disk and missing from every stable menu. This script makes the menus follow
the pages:

  - English stable groups = the dev groups, with <product>/dev/ -> <product>/stable/.
    A page whose stable file does not exist is left out and reported.
  - Each locale's stable groups = the English stable groups without the Guides
    and Tutorial groups (neither is translated), with every page path prefixed
    by "<lang>/". A page with no translated file (every extension page, and a
    new page before the translation lands) points at the English page instead,
    as the locale menus already do. Run the script again after the translation
    lands to switch those pages to their translations.

Running it on an unchanged tree changes nothing.

Usage:
    python3 scripts/sync-stable-nav.py [--product mysql-9.7] [--dry-run] [--repo PATH]
"""

import argparse
import json
import sys
from pathlib import Path

LOCALES = ["ja", "ko", "zh", "pt-BR"]
UNTRANSLATED_GROUPS = {"Guides", "Tutorial"}


def map_paths(node, fn):
    """Apply fn to every page path (a string, or a "root") under node."""
    if isinstance(node, str):
        return fn(node)
    if isinstance(node, list):
        return [x for x in (map_paths(n, fn) for n in node) if x is not None]
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == "root":
                v = fn(v)
                if v is None:
                    continue
            elif k in ("pages", "groups"):
                v = map_paths(v, fn)
            out[k] = v
        if not out.get("pages", True) and not out.get("groups", True) and "root" not in out:
            return None  # every page of this group was left out
        return out
    return node


def page_list(node):
    found = []
    map_paths(node, lambda p: found.append(p) or p)
    return found


def sync(docs, product, repo):
    """Return (docs, report lines). docs is modified in place."""
    label = product.replace("mysql-", "MySQL ", 1)
    prod = next((p for p in docs["navigation"]["products"]
                 if p.get("product") == label), None)
    if prod is None:
        raise SystemExit(f"error: product {label!r} not in docs.json")
    by_kind = {v["version"].split(" ")[0]: v for v in prod["versions"]}
    dev, stable = by_kind.get("Development"), by_kind.get("Stable")
    if dev is None or stable is None:
        raise SystemExit(f"error: {label} needs a Development and a Stable version")

    dev_prefix, stable_prefix = f"{product}/dev/", f"{product}/stable/"
    report = []

    def to_stable(p):
        sp = stable_prefix + p[len(dev_prefix):] if p.startswith(dev_prefix) else p
        if (repo / f"{sp}.mdx").exists():
            return sp
        report.append(f"en: left out {sp} (no such page; run promote-release.py first?)")
        return None

    en_groups = map_paths(dev["groups"], to_stable)

    langs = {entry["language"]: entry for entry in stable["languages"]}
    for lang, entry in langs.items():
        if lang == "en":
            new_groups = en_groups
        else:
            def localize(p, lang=lang):
                lp = f"{lang}/{p}"
                return lp if (repo / f"{lp}.mdx").exists() else p

            new_groups = map_paths(
                [g for g in en_groups if g.get("group") not in UNTRANSLATED_GROUPS],
                localize)
        old_pages, new_pages = set(page_list(entry["groups"])), set(page_list(new_groups))
        for p in sorted(new_pages - old_pages):
            english = lang != "en" and not p.startswith(f"{lang}/")
            report.append(f"{lang}: add {p}" + (" (English page: no translation yet)" if english else ""))
        for p in sorted(old_pages - new_pages):
            report.append(f"{lang}: remove {p}")
        if new_groups != entry["groups"] and not (new_pages ^ old_pages):
            report.append(f"{lang}: reorder or regroup pages")
        entry["groups"] = new_groups
    return docs, report


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--product", default="mysql-8.4")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo", default=None)
    args = ap.parse_args()

    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parent.parent
    path = repo / "docs.json"
    before = path.read_text()
    docs, report = sync(json.loads(before), args.product, repo)
    after = json.dumps(docs, indent=2, ensure_ascii=False) + "\n"

    tag = "[plan] " if args.dry_run else ""
    for line in report:
        print(f"{tag}{args.product} {line}")
    if after == before:
        print(f"{args.product}: stable navigation already matches dev")
    elif not args.dry_run:
        path.write_text(after)
        print(f"{args.product}: docs.json updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
