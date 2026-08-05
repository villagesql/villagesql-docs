#!/usr/bin/env python3
"""Cut a release under the fixed stable/dev slot model.

The version number is NOT in the URL: current stable always lives at
`mysql-8.4/stable/`, dev at `mysql-8.4/dev/`. Cutting a release does not move
any live URL — it freezes the outgoing stable into a numbered archive and
promotes dev into the stable slot. It also keeps every version *number*
resolving: the current stable's number redirects to /stable/, and a superseded
number becomes its own frozen archive — nothing ever 404s. (`gen-redirects.py`
is only for one-off structural URL moves.)

Steps (example: stable 0.0.5 -> 0.0.6, dev opens 0.0.7-dev):
  1. snapshot mysql-8.4/stable (+ locales) -> mysql-8.4/0.0.5, freeze its
     self-links stable/ -> 0.0.5/, and noindex it.
  2. promote: mysql-8.4/dev -> mysql-8.4/stable (EN), rewrite dev/ -> stable/
     links. Locale stable dirs keep the previous translations until
     re-translated (VERSIONING.md step: Translate).
  3. scaffold new mysql-8.4/dev from the new stable (dev is indexed and
     self-canonical — no cross-canonical, so new features stay findable).
  4. docs.json: insert the archived version entry, bump the two version labels,
     and update redirects — drop the outgoing number's redirect (freeing its
     archive), repoint the outgoing -dev redirects to the shipped number, and
     add the new stable number's redirect -> /stable/.

Usage:
    python3 scripts/promote-release.py --old-stable 0.0.5 --new-stable 0.0.6 \
        --new-dev 0.0.7-dev [--dry-run] [--repo PATH]

--dry-run prints the plan (and the archived-entry JSON) without touching disk.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

PRODUCT = "mysql-8.4"
LOCALES = ["", "ja", "ko", "zh", "pt-BR"]  # "" = English tree at repo root


def slot_dirs(repo: Path, slot: str):
    """Existing <locale>/mysql-8.4/<slot> dirs across locales."""
    for loc in LOCALES:
        d = (repo / loc / PRODUCT / slot) if loc else (repo / PRODUCT / slot)
        if d.is_dir():
            yield d


def rewrite_prefix(d: Path, old: str, new: str) -> int:
    n = 0
    for p in d.rglob("*.mdx"):
        t = p.read_text(encoding="utf-8")
        if old in t:
            p.write_text(t.replace(old, new), encoding="utf-8")
            n += 1
    return n


def archived_entry(repo: Path, old_stable: str) -> str:
    """Derive the archived version entry from the current stable entry:
    relabel to the bare number, drop default, repoint stable/ paths to the
    numbered dir. Returned as a JSON block to paste into navigation.versions."""
    docs = json.loads((repo / "docs.json").read_text())
    stable_label = f"Stable ({old_stable})"

    def find(node):
        if isinstance(node, dict):
            if node.get("version") == stable_label:
                return node
            for v in node.values():
                r = find(v)
                if r:
                    return r
        elif isinstance(node, list):
            for v in node:
                r = find(v)
                if r:
                    return r
        return None

    entry = find(docs["navigation"])
    if entry is None:
        return f"// could not find version entry {stable_label!r}"
    entry = json.loads(json.dumps(entry))  # deep copy
    entry["version"] = old_stable
    entry.pop("default", None)

    def repath(node):
        if isinstance(node, dict):
            return {k: repath(v) for k, v in node.items()}
        if isinstance(node, list):
            return [repath(v) for v in node]
        if isinstance(node, str):
            return node.replace(f"{PRODUCT}/stable/", f"{PRODUCT}/{old_stable}/")
        return node

    entry = repath(entry)
    return json.dumps(entry, indent=2, ensure_ascii=False)


def _matching_brace(text: str, open_pos: int) -> int:
    """Index of the `}` matching the `{` at open_pos, skipping string contents."""
    depth = 0
    in_str = esc = False
    for i in range(open_pos, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _matching_bracket(text: str, open_pos: int) -> int:
    """Index of the `]` matching the `[` at open_pos, skipping string contents."""
    depth = 0
    in_str = esc = False
    for i in range(open_pos, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return i
    return -1


def insert_archived_entry(text: str, old_stable: str, entry_json: str) -> str:
    """Splice the archived version entry into docs.json right after the Stable
    entry, preserving surrounding formatting (no full reserialize)."""
    marker = f'"Stable ({old_stable})"'
    m = text.index(marker)
    open_pos = text.rfind("{", 0, m)
    close_pos = _matching_brace(text, open_pos)
    if close_pos == -1:
        raise ValueError("could not find the Stable entry's closing brace")
    indent = text[text.rfind("\n", 0, open_pos) + 1:open_pos]
    j = close_pos + 1
    while j < len(text) and text[j] in " \t":
        j += 1
    if j >= len(text) or text[j] != ",":
        raise ValueError("expected a comma after the Stable entry")
    indented = "\n".join(indent + ln for ln in entry_json.split("\n"))
    return text[:j + 1] + "\n" + indented + "," + text[j + 1:]


def manage_redirects(text: str, repo: Path, old_stable: str, new_stable: str):
    """Update the docs.json redirect array for a cut. Returns (new_text, stats).

    - Remove the outgoing stable's number redirects, so its freshly-frozen
      archive is reachable at /mysql-8.4/<old>/ instead of shadowed.
    - Repoint the outgoing dev's -dev redirects from /dev/ to the shipped
      number, so old dev links track what actually released.
    - Add the incoming stable's number redirects -> /stable/, so the current
      stable resolves at its number too. Every version number thus resolves.

    Re-emits the array in the established format so unchanged entries diff clean.
    """
    redirects = json.loads(text).get("redirects", [])
    old_pref = f"/{PRODUCT}/{old_stable}"
    dev_pref = f"/{PRODUCT}/{new_stable}-dev"
    dev_dest = f"/{PRODUCT}/dev"
    removed = repointed = 0
    out = []
    for r in redirects:
        s = r["source"]
        if s == old_pref or s.startswith(old_pref + "/"):
            removed += 1
            continue
        if s == dev_pref or s.startswith(dev_pref + "/"):
            d = r["destination"]
            if d == dev_dest or d.startswith(dev_dest + "/"):
                r = {"source": s,
                     "destination": f"/{PRODUCT}/{new_stable}" + d[len(dev_dest):]}
                repointed += 1
        out.append(r)

    stable_dir = repo / PRODUCT / "stable"
    adds = [(f"/{PRODUCT}/{new_stable}", f"/{PRODUCT}/stable")]
    for p in sorted(stable_dir.rglob("*.mdx")):
        slug = str(p.relative_to(stable_dir)).removesuffix(".mdx")
        adds.append((f"/{PRODUCT}/{new_stable}/{slug}", f"/{PRODUCT}/stable/{slug}"))
    out.extend({"source": s, "destination": d} for s, d in adds)

    arr_open = text.index("[", text.index('"redirects": ['))
    arr_close = _matching_bracket(text, arr_open)
    if arr_close == -1:
        raise ValueError("could not find end of redirects array")
    entries = []
    for i, r in enumerate(out):
        comma = "," if i < len(out) - 1 else ""
        entries.append(
            f'    {{\n      "source": "{r["source"]}",\n'
            f'      "destination": "{r["destination"]}"\n    }}{comma}')
    new_arr = "[\n" + "\n".join(entries) + "\n  ]"
    stats = {"removed": removed, "repointed": repointed, "added": len(adds)}
    return text[:arr_open] + new_arr + text[arr_close + 1:], stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-stable", required=True, help="outgoing stable number, e.g. 0.0.5")
    ap.add_argument("--new-stable", required=True, help="incoming stable number, e.g. 0.0.6")
    ap.add_argument("--new-dev", required=True, help="new dev label body, e.g. 0.0.7-dev")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo", default=None)
    args = ap.parse_args()

    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parent.parent
    scripts = repo / "scripts"
    old, new, ndev = args.old_stable, args.new_stable, args.new_dev
    dry = args.dry_run
    tag = "[plan] " if dry else ""

    en_stable = repo / PRODUCT / "stable"
    en_dev = repo / PRODUCT / "dev"
    if not en_stable.is_dir() or not en_dev.is_dir():
        print("error: mysql-8.4/stable and mysql-8.4/dev must both exist", file=sys.stderr)
        return 1
    if (repo / PRODUCT / old).exists():
        print(f"error: archive {PRODUCT}/{old} already exists", file=sys.stderr)
        return 1

    # 1. snapshot stable -> numbered archive, freeze self-links, noindex
    for d in slot_dirs(repo, "stable"):
        dest = d.parent / old
        print(f"{tag}snapshot {d.relative_to(repo)} -> {dest.relative_to(repo)}")
        if not dry:
            shutil.copytree(d, dest)
            rewrite_prefix(dest, f"{PRODUCT}/stable/", f"{PRODUCT}/{old}/")
    print(f"{tag}noindex archive {old} (via noindex-version.py)")
    if not dry:
        subprocess.run([sys.executable, str(scripts / "noindex-version.py"), old,
                        "--repo", str(repo)], check=True)

    # 2. promote dev -> stable (EN only; locales keep prior translations)
    print(f"{tag}promote {PRODUCT}/dev -> {PRODUCT}/stable (dev/ -> stable/ links)")
    if not dry:
        shutil.rmtree(en_stable)
        shutil.copytree(en_dev, en_stable)
        rewrite_prefix(en_stable, f"{PRODUCT}/dev/", f"{PRODUCT}/stable/")

    # 3. scaffold new dev from new stable (dev is self-canonical, no re-stamp)
    print(f"{tag}scaffold {PRODUCT}/dev from new stable")
    if not dry:
        shutil.rmtree(en_dev)
        shutil.copytree(en_stable, en_dev)

    # 4. docs.json: archived version entry, labels, and redirect lifecycle
    docs_path = repo / "docs.json"
    text = docs_path.read_text()
    entry_json = archived_entry(repo, old)
    text = insert_archived_entry(text, old, entry_json)
    print(f"{tag}insert archived version entry {old!r} after the Stable entry")
    subs = [(f"Stable ({old})", f"Stable ({new})"),
            (f"Development ({new}-dev)", f"Development ({ndev})")]
    for a, b in subs:
        if a not in text:
            print(f"error: label {a!r} not found in docs.json", file=sys.stderr)
            return 1
        text = text.replace(a, b)
        print(f"{tag}label: {a!r} -> {b!r}")
    text, rstats = manage_redirects(text, repo, old, new)
    print(f"{tag}redirects: remove {rstats['removed']} (/{PRODUCT}/{old}/*), "
          f"repoint {rstats['repointed']} ({new}-dev -> {new}), "
          f"add {rstats['added']} (/{PRODUCT}/{new}/*)")
    json.loads(text)  # validate the full transformation (runs in dry-run too)
    if dry:
        print(f"{tag}archived entry that would be inserted:\n{entry_json}")
    else:
        docs_path.write_text(text)
        print("docs.json updated and re-validated.")

    print("\nManual follow-ups (VERSIONING.md): re-translate locale stable, "
          "update content version-number prose, website + freshness.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
