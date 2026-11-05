#!/usr/bin/env python3
"""Switch-day step 3d: build the ja, ko, zh and pt-BR menus from the English menu.

    python3 scripts/build-translated-menus.py <docs-worktree> [--dry-run]

Each translated menu is a copy of the English menu (tabs, menus, groups and
their order) in which every page is replaced by its translation when the
translated file exists, and dropped when it does not. A group, menu item or tab
left with no pages is dropped too. Labels stay in English, as the live
translated menus have them today. Run it after the page move and the en/ step,
or on any layout: it reads the English page path, removes a leading en/, and
looks for <lang>/<rest>.
"""

import argparse
import copy
import json
import sys
from pathlib import Path

LANGS = ["ja", "ko", "zh", "pt-BR"]
CONTAINERS = ("tabs", "menu", "groups", "pages", "dropdowns", "anchors")


def translated(page, lang, repo):
    rest = page[3:] if page.startswith("en/") else page
    target = f"{lang}/{rest}"
    return target if (repo / f"{target}.mdx").is_file() else None


def rebuild(node, lang, repo):
    """Return the node with translated pages, or None when nothing is left."""
    if isinstance(node, str):
        if "://" in node:
            return None
        return translated(node, lang, repo)
    if isinstance(node, list):
        kept = [x for x in (rebuild(n, lang, repo) for n in node) if x is not None]
        return kept or None
    if isinstance(node, dict):
        out, has_content = {}, False
        for k, v in node.items():
            if k in CONTAINERS:
                r = rebuild(v, lang, repo)
                if r is not None:
                    out[k] = r
                    has_content = True
            elif k == "root":
                r = rebuild(v, lang, repo)
                if r is not None:
                    out[k] = r
                    has_content = True
            elif k == "href":
                # External links (navbar-style tab or menu links) carry over.
                out[k] = v
                has_content = has_content or "://" in str(v)
            else:
                out[k] = v
        return out if has_content else None
    return node


def count(node):
    if isinstance(node, str):
        return 1
    if isinstance(node, list):
        return sum(count(n) for n in node)
    if isinstance(node, dict):
        return sum(count(v) for k, v in node.items() if k in CONTAINERS or k == "root")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    docs = json.loads((repo / "docs.json").read_text())
    langs = docs["navigation"]["languages"]
    english = next((l for l in langs if l["language"] == "en"), None)
    if english is None:
        sys.exit("stopped: docs.json has no English language entry")
    out = [english]
    for lang in LANGS:
        old = next((l for l in langs if l["language"] == lang), {"language": lang})
        entry = {k: v for k, v in old.items() if k not in CONTAINERS}
        entry["language"] = lang
        entry.pop("default", None)
        for k in CONTAINERS:
            if k in english:
                r = rebuild(copy.deepcopy(english[k]), lang, repo)
                if r is not None:
                    entry[k] = r
        print(f"{lang}: {count(entry)} pages in the menu (was {count(old)})")
        out.append(entry)
    if a.dry_run:
        return
    docs["navigation"]["languages"] = out
    (repo / "docs.json").write_text(json.dumps(docs, indent=2, ensure_ascii=False) + "\n")
    print("done")


main()
