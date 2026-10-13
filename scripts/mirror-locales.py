#!/usr/bin/env python3
"""Make one product's translated pages from another product's translations.

The 9.7 docs are the 8.4 docs with version tokens swapped and a few paragraphs
reworded. So the 9.7 translations come from the 8.4 translations, not from a
second translation run:

  1. Apply the token map to <lang>/<from>/<slot>/<page>: page paths, version
     ids (mysql-8.4_ -> mysql-9.7_), upstream manual URLs, and the MySQL
     version from each product's English index.mdx.
  2. Replace every fenced code block with the block at the same position in
     the English <to> page. Translations never change code blocks, so the
     English target has the right commands and output.
  3. Check the token map against English: apply it to the English <from> page
     and compare with the English <to> page. Where they still differ, the <to>
     wording is not a token swap (or a code block moved), and the script prints
     both sides. In the written locale page, remove the translation of each -
     line, translate each + line, and move any [code block N] that moved.
  4. Check each listed page: every code span and link in the listed lines must
     occur as often in the locale page as in the English <to> page, and where a
     code block moved, the blocks must sit between the same paragraphs.

Every page of the English <to> slot is written, for every language. Pages
with no <from> translation (the extension pages are never translated) are
listed and skipped. A page whose code blocks do not line up with the English
<to> page is skipped: its <from> translation is behind its English page, so
translate it again first.

The script exits 1 until every listed page passes step 4. A run without
--check writes the pages again and undoes the hand translation, so after the
hand edits run only --check.

Usage:
    python3 scripts/mirror-locales.py [--from mysql-8.4] [--to mysql-9.7]
        [--slot stable] [--langs ja,ko,zh,pt-BR] [--dry-run | --check] [--repo PATH]
"""

import argparse
import difflib
import re
import sys
from collections import Counter
from pathlib import Path

FENCE = re.compile(r"^([ \t]*)(```+|~~~+).*?^\1\2[ \t]*$", re.M | re.S)
COMPAT = re.compile(r"compatible with MySQL (\d+\.\d+\.\d+)")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
LINK = re.compile(r"\]\(([^)\s]+)\)|href=\"([^\"]+)\"")


def mysql_version(repo, product, slot):
    text = (repo / product / slot / "index.mdx").read_text()
    m = COMPAT.search(text)
    if not m:
        raise SystemExit(f"error: no 'compatible with MySQL x.y.z' in {product}/{slot}/index.mdx")
    return m.group(1)


def token_map(repo, src, dst, slot):
    s_num, d_num = src.split("-", 1)[1], dst.split("-", 1)[1]
    return [
        (f"/{src}/", f"/{dst}/"),
        (f"{src}_", f"{dst}_"),
        (mysql_version(repo, src, slot), mysql_version(repo, dst, slot)),
        (f"dev.mysql.com/doc/refman/{s_num}/", f"dev.mysql.com/doc/refman/{d_num}/"),
        (f"dev.mysql.com/doc/extending-mysql/{s_num}/", f"dev.mysql.com/doc/extending-mysql/{d_num}/"),
        (f"MySQL {s_num}", f"MySQL {d_num}"),
    ]


def apply(text, tokens):
    for a, b in tokens:
        text = text.replace(a, b)
    return text


def swap_fences(text, english):
    """Replace text's fenced blocks, in order, with english's. None if counts differ."""
    theirs = list(FENCE.finditer(english))
    if len(list(FENCE.finditer(text))) != len(theirs):
        return None
    blocks = iter(m.group(0) for m in theirs)
    return FENCE.sub(lambda _m: next(blocks), text)


def prose_lines(text):
    """Lines with each fenced block reduced to a numbered placeholder."""
    n = iter(range(1, 10**6))
    return FENCE.sub(lambda _m: f"[code block {next(n)}]", text).splitlines()


def invariants(text, lang=None):
    """Code spans and link targets outside code blocks, with the language prefix removed."""
    found = Counter()
    for line in prose_lines(text):
        found.update(f"`{c}`" for c in CODE_SPAN.findall(line))
        for a, b in LINK.findall(line):
            target = (a or b).split("#")[0]
            if lang and target.startswith(f"/{lang}/"):
                target = target[len(lang) + 1:]
            found[f"link {target}"] += 1
    return found


def layout(text):
    """Text and code blocks in page order, with runs of text paragraphs merged."""
    kinds = []
    for chunk in re.split(r"\n\s*\n", "\n".join(prose_lines(text))):
        kind = "code" if chunk.strip().startswith("[code block") else "text"
        if chunk.strip() and not (kinds and kinds[-1] == kind == "text"):
            kinds.append(kind)
    return kinds


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from", dest="src", default="mysql-8.4")
    ap.add_argument("--to", dest="dst", default="mysql-9.7")
    ap.add_argument("--slot", default="stable")
    ap.add_argument("--langs", default="ja,ko,zh,pt-BR")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--check", action="store_true",
                      help="write nothing; only check the hand-translated pages")
    ap.add_argument("--repo", default=None)
    args = ap.parse_args()

    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parent.parent
    src, dst, slot = args.src, args.dst, args.slot
    langs = args.langs.split(",")
    tokens = token_map(repo, src, dst, slot)
    en_dst_root = repo / dst / slot
    pages = sorted(p.relative_to(en_dst_root) for p in en_dst_root.rglob("*.mdx"))
    tag = "[plan] " if args.dry_run else ""

    # English check, once per page: where does the token map not explain <to>?
    by_hand = {}
    for rel in pages:
        en_src = repo / src / slot / rel
        if not en_src.exists():
            continue
        mapped = prose_lines(apply(en_src.read_text(), tokens))
        target = prose_lines((en_dst_root / rel).read_text())
        diff = [l for l in difflib.unified_diff(mapped, target, lineterm="", n=0)
                if l[:1] in "+-" and l[:3] not in ("+++", "---") and l[1:].strip()]
        if diff:
            by_hand[rel] = diff

    problems = 0
    if not args.check:
        for lang in langs:
            written, untranslated = 0, []
            for rel in pages:
                loc_src = repo / lang / src / slot / rel
                if not loc_src.exists():
                    untranslated.append(str(rel.with_suffix("")))
                    continue
                out = swap_fences(apply(loc_src.read_text(), tokens), (en_dst_root / rel).read_text())
                if out is None:
                    print(f"{tag}{lang}: {rel} has a different number of code blocks than "
                          f"the English {dst} page; skipped")
                    problems += 1
                    continue
                if not args.dry_run:
                    dest = repo / lang / dst / slot / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(out)
                written += 1
            loc_root = repo / lang / dst / slot
            for p in sorted(loc_root.rglob("*.mdx")):
                if not (en_dst_root / p.relative_to(loc_root)).exists():
                    print(f"{tag}{lang}: {p.relative_to(repo)} has no English page; not touched")
            if untranslated:
                print(f"{tag}{lang}: {len(untranslated)} pages have no {src} translation; skipped: "
                      + ", ".join(untranslated))
            print(f"{tag}{lang}: wrote {written} pages to {lang}/{dst}/{slot}/")

        if by_hand:
            print(f"\nTranslate by hand: on these pages the English {dst} wording is not a "
                  f"token swap of {src}. In each locale page, remove the translation of every "
                  f"- line, translate every + line, and move any code block that moved. "
                  f"Then run this script with --check.")
            for rel, diff in by_hand.items():
                print(f"\n  {rel}")
                for l in sorted(diff, key=lambda l: l[0] != "-"):
                    print(f"    {l[0]} {l[1:]}")

    if args.dry_run:
        return 1 if problems else 0

    # Check the hand-translated pages: the code spans and links of the listed
    # lines must occur as often in each locale page as in the English page.
    failed = 0
    for rel, diff in by_hand.items():
        watched = set(invariants("\n".join(l[1:] for l in diff)))
        en_text = (en_dst_root / rel).read_text()
        english = invariants(en_text)
        block_moved = any(l[1:].strip().startswith("[code block") for l in diff)
        for lang in langs:
            page = repo / lang / dst / slot / rel
            if not page.exists():
                continue
            ours = invariants(page.read_text(), lang)
            wrong = [f"{t} {ours[t]}x, English {english[t]}x"
                     for t in sorted(watched) if ours[t] != english[t]]
            if block_moved and layout(page.read_text()) != layout(en_text):
                wrong.append("code blocks are not between the same paragraphs as in English")
            if wrong:
                failed += 1
                print(f"not done: {page.relative_to(repo)}: " + "; ".join(wrong))
    if by_hand and not failed:
        print("hand-translated pages: check passed")
    return 1 if problems or failed else 0


if __name__ == "__main__":
    sys.exit(main())
