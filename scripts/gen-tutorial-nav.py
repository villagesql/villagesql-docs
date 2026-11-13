#!/usr/bin/env python3
"""List the tutorial lessons in the navigation, and in the tutorial hub page.

The tutorial is one ordered curriculum, so its order has to be identical in
three places: the sidebar, the table of contents on tutorial/index.mdx, and the
prev/next chain Mintlify builds from the sidebar. Keeping those in step by hand
across the navigation blocks is the failure this script removes. The order
lives in scripts/tutorial-toc.json and nowhere else.

Run it after adding a lesson, renaming a lesson, or reordering the curriculum:

    python3 scripts/gen-tutorial-nav.py        # from the repo root

Three things shape the layout, and each one looks like a mistake until you know
why it is there:

1. Only lessons that exist on disk are listed. The manifest carries the whole
   curriculum from the start, and the sections land one pull request at a time,
   so a manifest entry with no page behind it is the normal state rather than
   an error. Mintlify reports a page it cannot find as a broken navigation
   entry, which would fail the build, so an absent lesson is skipped and named
   in the run output instead.

2. The group sits in the Guides tab, which has no release versions. The hub
   page is its first entry, so the heading looks like every other group
   heading in the tab.

3. The group goes into the English navigation only. scripts/build-translated-
   menus.py copies it into each translated menu, keeping the lessons that
   have a translated file. The contents list on a translated tutorial/index.mdx
   is not generated, so a change to the lesson order is made there by hand.
"""

import glob
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOC = os.path.join(REPO, "scripts", "tutorial-toc.json")
DOCS_JSON = os.path.join(REPO, "docs.json")
# English pages live under en/ once the site moves them there; the menu paths
# and the links on the hub page follow. The manifest stays layout-free.
EN = "en/" if glob.glob(os.path.join(REPO, "en", "**", "*.mdx"), recursive=True) else ""
TUTORIAL = os.path.join(REPO, EN, "tutorial")

BEGIN = "{/* BEGIN GENERATED CONTENTS. Edit scripts/tutorial-toc.json, then run scripts/gen-tutorial-nav.py */}"
END = "{/* END GENERATED CONTENTS */}"


def load_toc():
    toc = json.load(open(TOC))
    seen = set()
    for section in toc["sections"]:
        for lesson in section["lessons"]:
            slug = lesson["slug"]
            if slug in seen:
                sys.exit(f"duplicate slug in the manifest: {slug}")
            seen.add(slug)
    return toc


def present(slug):
    return os.path.exists(os.path.join(TUTORIAL, f"{slug}.mdx"))


def guides_groups(docs):
    """The groups array of the English Guides tab."""
    for language in docs["navigation"]["languages"]:
        if language.get("language") != "en":
            continue
        for tab in language["tabs"]:
            if tab.get("tab") == toc_tab():
                return tab["groups"]
    sys.exit(f"docs.json has no English tab named {toc_tab()!r}")


def toc_tab():
    return load_toc()["tab"]


def build_group(toc, listed):
    """The Tutorial group, as Mintlify wants it: subgroups of page paths."""
    pages = []
    for section in toc["sections"]:
        slugs = [l["slug"] for l in section["lessons"] if l["slug"] in listed]
        if slugs:
            pages.append({
                "group": section["title"],
                "pages": [f"{EN}tutorial/{s}" for s in slugs],
            })
    # Before the first lesson lands, the group would otherwise carry an empty
    # pages array, which lists nothing and leaves the hub page unreachable from
    # the sidebar. Falling back to the hub keeps the navigation valid while the
    # sections are still being written.
    return {"group": toc["group"], "pages": [EN + toc["root"]] + pages}


def update_navigation(group):
    docs = json.load(open(DOCS_JSON))
    groups = guides_groups(docs)
    names = [g.get("group") for g in groups]
    if group["group"] in names:
        groups[names.index(group["group"])] = group
    else:
        groups.insert(0, group)
    json.dump(docs, open(DOCS_JSON, "w"), indent=2, ensure_ascii=False)
    open(DOCS_JSON, "a").write("\n")


def update_hub(toc, listed):
    """Rewrite the contents list on the hub page, between the two markers."""
    path = os.path.join(TUTORIAL, "index.mdx")
    if not os.path.exists(path):
        return False
    lines = []
    number = 0
    for section in toc["sections"]:
        rows = [l for l in section["lessons"] if l["slug"] in listed]
        if not rows:
            continue
        number += 1
        lines.append(f"### {number}. {section['title']}")
        lines.append("")
        for lesson in rows:
            lines.append(f"- [{lesson['label']}](/{EN}tutorial/{lesson['slug']})")
        lines.append("")
    contents = "\n".join(lines).rstrip()
    body = BEGIN + "\n\n" + contents + "\n\n" + END if contents else BEGIN + "\n" + END
    text = open(path).read()
    if BEGIN not in text or END not in text:
        sys.exit(f"{path} is missing the generated-contents markers")
    text = re.sub(
        re.escape(BEGIN) + r".*?" + re.escape(END), lambda _: body, text, flags=re.S
    )
    open(path, "w").write(text)
    return True


def main():
    toc = load_toc()
    planned = [l["slug"] for s in toc["sections"] for l in s["lessons"]]
    listed = {s for s in planned if present(s)}
    missing = [s for s in planned if s not in listed]

    update_navigation(build_group(toc, listed))
    hub = update_hub(toc, listed)

    print(f"listed {len(listed)} of {len(planned)} lessons in the {toc['tab']} tab")
    print(f"rewrote the contents list on {EN}tutorial/index.mdx" if hub
          else f"{EN}tutorial/index.mdx does not exist yet, so no contents list was written")
    if missing:
        print(f"not written yet, so left out: {', '.join(missing)}")


if __name__ == "__main__":
    main()
