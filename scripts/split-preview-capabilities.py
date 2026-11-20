#!/usr/bin/env python3
"""Split one language's Preview Capabilities page into an overview and subpages.

    python3 scripts/split-preview-capabilities.py <lang> [--dry-run]

Reads <lang>/extensions/build/preview-capabilities.mdx, cuts it at its `##`
headings (outside code blocks) and writes each section, unchanged, to the page
that scripts/preview-pages.json assigns it by position. The overview keeps the
intro and its own sections at the same URL; each subpage gets front matter
(audience, title, description) and a lead sentence from the language's entry in
the same file.

It also:
- adds `{#id}` to a translated `##` heading that has none, so every section
  keeps the English anchor;
- rewrites a link to `#anchor` whose heading now lives on another page;
- points each Capability Index row at the section that documents it;
- rewrites links in <lang>/ shared pages (not the release copies under
  <lang>/8.4 and <lang>/9.7) that point to a moved anchor on the old page.

Run it once per language, before adding the new pages to docs.json. It stops
if the page does not have the expected number of sections, so a second run on
an already split page changes nothing.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "scripts" / "preview-pages.json"
OVERVIEW = "preview-capabilities"

HEADING = re.compile(r"^(#{2,6})\s+(.*?)\s*(?:\{#([^}]+)\})?\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def slugify(text):
    """Mintlify's anchor for a heading without a custom id."""
    text = re.sub(r"`", "", text.lower())
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text.strip())


def headings(lines):
    """Yield (index, level, text, custom_id) for headings outside code blocks."""
    in_code = False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = HEADING.match(line)
        if m:
            yield i, len(m.group(1)), m.group(2), m.group(3)


def split_front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        sys.exit("no front matter")
    return m.group(1), text[m.end():]


def front_matter(audience, title, description):
    return (
        "---\n"
        f"audience: {audience}\n"
        f"title: {json.dumps(title, ensure_ascii=False)}\n"
        f"description: {json.dumps(description, ensure_ascii=False)}\n"
        "---\n"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lang")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = json.loads(CONFIG.read_text())
    lc = cfg["languages"].get(args.lang)
    if lc is None:
        sys.exit(f"no entry for {args.lang} in {CONFIG}")
    sections_cfg = cfg["sections"]
    base = f"/{args.lang}/extensions/build"
    src = ROOT / args.lang / "extensions" / "build" / f"{OVERVIEW}.mdx"

    fm, body = split_front_matter(src.read_text())
    lines = body.split("\n")

    # Cut at the level-2 headings.
    cuts = [h for h in headings(lines) if h[1] == 2]
    if len(cuts) != len(sections_cfg):
        sys.exit(
            f"{src}: found {len(cuts)} `##` sections, expected "
            f"{len(sections_cfg)}; already split, or the page changed"
        )
    intro = lines[: cuts[0][0]]
    sections = []
    for n, (i, _, text, cid) in enumerate(cuts):
        end = cuts[n + 1][0] if n + 1 < len(cuts) else len(lines)
        want = sections_cfg[n]["id"]
        got = cid or slugify(text)
        if args.lang == "en" and got != want:
            sys.exit(f"section {n} is #{got}, expected #{want}")
        sec = lines[i:end]
        if args.lang != "en" and cid is None:
            sec[0] = f"## {text} {{#{want}}}"
        elif cid is not None and cid != want:
            sys.exit(f"section {n} has {{#{cid}}}, expected {{#{want}}}")
        sections.append((want, sections_cfg[n]["page"], text, sec))

    # Every anchor on the old page, and the page it now lives on.
    anchor_page = {}
    for _, page, _, sec in sections:
        for _, _, text, cid in headings(sec):
            anchor_page.setdefault(cid or slugify(text), page)
    for _, _, text, cid in headings(intro):
        anchor_page.setdefault(cid or slugify(text), OVERVIEW)

    # Group the sections by page, in the order the config lists them.
    pages = {}
    for sec in sections:
        pages.setdefault(sec[1], []).append(sec)

    def first_on_page(sid):
        page = next(s[1] for s in sections if s[0] == sid)
        return pages[page][0][0] == sid

    def url(page, anchor=None):
        u = f"{base}/{page}"
        return f"{u}#{anchor}" if anchor else u

    def fix_local_links(text, page):
        def repl(m):
            a = m.group(1)
            target = anchor_page.get(a)
            if target is None:
                sys.exit(f"link to #{a} matches no heading on the old page")
            return m.group(0) if target == page else f"]({url(target, a)})"
        return re.sub(r"\]\(#([^)\s]+)\)", repl, text)

    def fix_index(text):
        out = []
        for line in text.split("\n"):
            m = re.match(r"^\| `([^`]+)` \|(.*)\|\s*$", line)
            if m and m.group(1) in cfg["capabilities"]:
                sid = cfg["capabilities"][m.group(1)]
                sec = next(s for s in sections if s[0] == sid)
                cells = m.group(2).split("|")
                link = url(sec[1], None if first_on_page(sid) else sid)
                cells[-1] = " " + lc["index_cell"].format(label=sec[2], url=link) + " "
                line = f"| `{m.group(1)}` |" + "|".join(cells) + "|"
            out.append(line)
        return "\n".join(out)

    outputs = {}
    for page, secs in pages.items():
        text = "\n".join(l for s in secs for l in s[3]).rstrip("\n") + "\n"
        if page == OVERVIEW:
            text = "\n".join(intro) + "\n" + text
            text = fix_index(fix_local_links(text, page))
            desc = lc["pages"][OVERVIEW]["description"]
            new_fm = re.sub(
                r"^description: .*$",
                lambda _: f"description: {json.dumps(desc, ensure_ascii=False)}",
                fm, flags=re.M,
            )
            outputs[src] = f"---\n{new_fm}\n---\n" + text
        else:
            pc = lc["pages"][page]
            audience = re.search(r"^audience: (.*)$", fm, re.M).group(1)
            lead = lc["lead"].format(overview=url(OVERVIEW))
            text = fix_local_links(text, page)
            outputs[src.with_name(f"{page}.mdx")] = (
                front_matter(audience, pc["title"], pc["description"])
                + "\n" + lead + "\n\n" + text
            )

    # Links from other shared pages to an anchor that moved.
    old = re.compile(rf"{re.escape(base)}/{OVERVIEW}#([\w-]+)")
    for f in sorted((ROOT / args.lang).rglob("*.mdx")):
        rel = f.relative_to(ROOT / args.lang).parts
        if rel[0] in ("8.4", "9.7") or f in outputs:
            continue
        text = f.read_text()

        def repl(m):
            target = anchor_page.get(m.group(1))
            if target is None:
                sys.exit(f"{f}: link to #{m.group(1)} matches no heading")
            return m.group(0) if target == OVERVIEW else url(target, m.group(1))
        new = old.sub(repl, text)
        if new != text:
            outputs[f] = new

    for f, text in outputs.items():
        print(f"{'would write' if args.dry_run else 'wrote'} "
              f"{f.relative_to(ROOT)} ({len(text.encode())} bytes)")
        if not args.dry_run:
            f.write_text(text)


if __name__ == "__main__":
    main()
