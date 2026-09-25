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

2. The group goes into the live version slots only, never into the frozen
   archives. An archive is a snapshot of what shipped with that release, and
   the tutorial did not. This matches how the Guides group already sits in
   archives with fewer subgroups than the live slots carry.

3. The group goes into English navigation blocks only. Nothing under tutorial/
   is translated, for the same reason nothing under guides/ is. VERSIONING.md
   is the operative statement of that rule.
"""

import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOC = os.path.join(REPO, "scripts", "tutorial-toc.json")
DOCS_JSON = os.path.join(REPO, "docs.json")

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
    return os.path.exists(os.path.join(REPO, "tutorial", f"{slug}.mdx"))


def live_group_arrays(docs):
    """The groups array of every live English navigation block.

    A version is live when its label names it as the development or the stable
    slot. Everything else is a frozen archive, which keeps the navigation it
    was frozen with.
    """
    arrays = []
    for product in docs["navigation"]["products"]:
        for version in product["versions"]:
            label = version.get("version", "")
            if not label.startswith(("Development", "Stable")):
                continue
            if "languages" in version:
                targets = [x for x in version["languages"] if x.get("language") == "en"]
            else:
                targets = [version]
            for target in targets:
                if isinstance(target.get("groups"), list):
                    arrays.append(target["groups"])
    return arrays


def build_group(toc, listed):
    """The Tutorial group, as Mintlify wants it: subgroups of page paths."""
    pages = []
    for section in toc["sections"]:
        slugs = [l["slug"] for l in section["lessons"] if l["slug"] in listed]
        if slugs:
            pages.append({
                "group": section["title"],
                "pages": [f"tutorial/{s}" for s in slugs],
            })
    # Before the first lesson lands, the group would otherwise carry an empty
    # pages array, which lists nothing and leaves the hub page unreachable from
    # the sidebar. Falling back to the hub keeps the navigation valid while the
    # sections are still being written.
    return {
        "group": toc["group"],
        "icon": toc["icon"],
        "pages": pages or [toc["root"]],
        "root": toc["root"],
    }


def update_navigation(group, before):
    docs = json.load(open(DOCS_JSON))
    count = 0
    for groups in live_group_arrays(docs):
        names = [g.get("group") for g in groups]
        if group["group"] in names:
            groups[names.index(group["group"])] = group
        elif before in names:
            groups.insert(names.index(before), group)
        else:
            groups.append(group)
        count += 1
    json.dump(docs, open(DOCS_JSON, "w"), indent=2, ensure_ascii=False)
    open(DOCS_JSON, "a").write("\n")
    return count


def update_hub(toc, listed):
    """Rewrite the contents list on the hub page, between the two markers."""
    path = os.path.join(REPO, "tutorial", "index.mdx")
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
            lines.append(f"- [{lesson['label']}](/tutorial/{lesson['slug']})")
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

    navs = update_navigation(build_group(toc, listed), toc["before_group"])
    hub = update_hub(toc, listed)

    print(f"listed {len(listed)} of {len(planned)} lessons in {navs} navigation blocks")
    print("rewrote the contents list on tutorial/index.mdx" if hub
          else "tutorial/index.mdx does not exist yet, so no contents list was written")
    if missing:
        print(f"not written yet, so left out: {', '.join(missing)}")


if __name__ == "__main__":
    main()
