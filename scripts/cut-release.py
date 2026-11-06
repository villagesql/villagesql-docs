#!/usr/bin/env python3
"""Cut a release in the one-copy layout of the redesigned docs.

Example: stable 0.0.7 -> 0.0.8, and the dev release becomes 0.0.9-dev.

    python3 scripts/cut-release.py --old 0.0.7 --new 0.0.8 --next 0.0.9-dev \
        --repo <docs-worktree> [--dry-run]

The layout it expects (the redesign after the switch-day move):
  - Server pages live per codebase: <codebase>/stable/ and <codebase>/dev/,
    for mysql-8.4 and mysql-9.7. Translated copies live under <lang>/. Once
    English moves under en/, every English path and address starts with en/,
    and the codebase folders may be named 8.4 and 9.7 instead. The script
    finds out which layout it is in when it starts.
  - Pages shared by every release live once, at addresses that match their tab:
    extensions/..., sdk/cpp/..., sdk/rust/..., and version-policy.
  - A difference in the coming release is a note on the shared page:
    <Info> ... **Changed in <new>-dev.** ... </Info>. The version string is
    what the script looks for, so the label may be translated.

What a cut does:
  1. Archive. For each codebase, the outgoing stable server pages are copied to
     <codebase>/<old>/, and the shared pages are copied in beside them under the
     flat names the 0.0.6 archive uses (create, rust-sdk, extensions/vsql-ai).
     Notes about <new>-dev are left out of the copies. Links inside the archive
     point at the archive. The archive gets noindex, and a group in the Past
     releases menu.
  2. Promote. Each codebase's dev server pages replace its stable server pages,
     and a new dev is copied from the new stable.
  3. Notes. On the shared pages, every <new>-dev note becomes normal page text.
     The script lists each one, so that a person can check the sentences around
     it.
  4. Labels and redirects. The dev menu groups, dev-releases.mdx, and
     past-releases.mdx name the new numbers, and every version number keeps
     resolving.
  5. A list of the server pages that still name the old release, for a person
     to update.

It stops before writing anything if an archive already exists, if a stable
server page has no dev counterpart, or if a dev note cannot be parsed.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

CODEBASES = ["mysql-8.4", "mysql-9.7"]  # or ["8.4", "9.7"]; set in main()
LANGS = ["ja", "ko", "zh", "pt-BR"]
EN = ""  # "en/" once English moves under en/; set in main()
PREFIXES = [""] + [lang + "/" for lang in LANGS]
LABEL = {"mysql-8.4": "MySQL 8.4", "mysql-9.7": "MySQL 9.7"}
END = r"(?=[)#\"'\s`>?]|$)"
# The stable schema, as extension manifests name it on GitHub.
SCHEMA_LINK = re.compile(r"(raw\.githubusercontent\.com/villagesql/villagesql-docs/[\w.-]+/mysql-(?:8\.4|9\.7))"
                         r"/stable/manifest\.json\.schema\.json")


# ---------------------------------------------------------------- docs.json --

def english(docs):
    return [l for l in docs["navigation"]["languages"] if l["language"] == "en"][0]


def tab(docs, name):
    return [t for t in english(docs)["tabs"] if t["tab"] == name][0]


def spellings(c):
    """Every name a codebase folder has had: 8.4 and mysql-8.4."""
    return {c, "mysql-" + c.removeprefix("mysql-")}


def bare(page):
    """An English menu path without its en/ prefix."""
    return page[len(EN):] if EN and page.startswith(EN) else page


def pages_in(node):
    """Every page path under a menu node, in menu order."""
    out = []
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, list):
        for item in node:
            out.extend(pages_in(item))
    elif isinstance(node, dict):
        # A group's own page (root) comes before the pages inside it.
        for key in ("root", "pages", "groups", "menu", "tabs", "languages"):
            if key in node:
                out.extend(pages_in(node[key]))
    return out


def flat_name(address, catalog):
    """A shared page's name inside an archive, as the 0.0.6 archive names it."""
    if address in catalog:
        return address  # extensions/vsql-ai stays extensions/vsql-ai
    if address == "extensions/catalog":
        return "extensions"
    for prefix, add in (("extensions/build/", ""), ("sdk/cpp/", ""), ("sdk/rust/", "rust-"), ("extensions/", "")):
        if address.startswith(prefix):
            return add + address[len(prefix):]
    return address  # version-policy


def shared_pages(docs):
    """Shared page address -> archive name, plus the menu groups they sit in."""
    catalog = set()
    for group in tab(docs, "Extensions")["groups"]:
        for sub in group["pages"]:
            # The extension pages sit in the group whose own page is the catalog.
            if isinstance(sub, dict) and str(sub.get("root", "")).endswith("extensions/catalog"):
                catalog.update(bare(p) for p in pages_in(sub["pages"]))
    shared = {}
    for name in ("Overview", "Extensions", "Reference"):
        for page in map(bare, pages_in(tab(docs, name))):
            if page.startswith(("extensions", "sdk/")) or page == "version-policy":
                shared[page] = flat_name(page, catalog)
    return shared


def pages_in_groups(node):
    """Every group dict under a menu node."""
    out = []
    if isinstance(node, dict):
        if "group" in node:
            out.append(node)
        for key in ("pages", "groups"):
            for item in node.get(key, []):
                out.extend(pages_in_groups(item))
    elif isinstance(node, list):
        for item in node:
            out.extend(pages_in_groups(item))
    return out


def rename(node, mapping):
    if isinstance(node, str):
        return mapping.get(node, node)
    if isinstance(node, list):
        return [rename(item, mapping) for item in node]
    if isinstance(node, dict):
        return {k: rename(v, mapping) for k, v in node.items()}
    return node


def archive_group(docs, codebase, old, shared):
    """The Past releases group for one codebase, built from today's menus."""
    server = tab(docs, "Server")
    items = {i["item"]: i for i in server["menu"]}
    stable_map = {}
    for page in pages_in(server):
        if page.startswith(EN + codebase + "/stable/"):
            stable_map[page] = page.replace("/stable/", f"/{old}/", 1)
    archive_map = {EN + p: f"{EN}{codebase}/{old}/{n}" for p, n in shared.items()}

    groups = []
    if LABEL[codebase] in items:
        groups.extend(rename(items[LABEL[codebase]]["groups"], stable_map))
    if codebase.endswith("8.4") and "Percona Server 8.4" in items:
        groups.append({"group": "Percona Server 8.4",
                       "pages": rename(items["Percona Server 8.4"]["groups"], stable_map)})
    for group in tab(docs, "Extensions")["groups"]:
        groups.append(rename(group, archive_map))
    sdk = [{"group": i["item"], "pages": rename(pages_in(i), archive_map)} for i in tab(docs, "Reference")["menu"]]
    groups.append({"group": "SDKs", "pages": sdk})
    first = [archive_map[EN + "version-policy"]] if EN + "version-policy" in archive_map else []
    return {"group": f"{LABEL[codebase]} · {old}", "pages": first + groups}


# ------------------------------------------------------------------- notes --

NOTE = re.compile(r"\n?<Info>\n(?P<body>.*?)\n</Info>\n?", re.S)


def note_blocks(text, version):
    """(match, body) for every <Info> block that mentions <version>-dev."""
    return [(m, m.group("body")) for m in NOTE.finditer(text) if f"{version}-dev" in m.group("body")]


def strip_notes(text, version):
    return NOTE.sub(lambda m: "\n" if f"{version}-dev" in m.group("body") else m.group(0), text)


def unwrap_notes(text, version):
    """Turn each <version>-dev note into a plain paragraph. Drops the bold label."""
    def plain(m):
        body = m.group("body")
        if f"{version}-dev" not in body:
            return m.group(0)
        body = re.sub(r"^\s*\*\*[^*\n]*" + re.escape(version) + r"-dev[^*\n]*\*\*\s*", "", body, count=1)
        return "\n" + body.strip() + "\n"
    return NOTE.sub(plain, text)


# ------------------------------------------------------------------- links --

def link_pattern(addresses):
    ordered = sorted(addresses, key=len, reverse=True)
    return re.compile(r"(?<![\w/.-])/(" + "|".join(re.escape(a) for a in ordered) + ")" + END)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--next", required=True, help="the new dev label, such as 0.0.9-dev")
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    repo, old, new, nxt, dry = a.repo.resolve(), a.old, a.new, a.next, a.dry_run
    global EN, PREFIXES, CODEBASES, LABEL
    EN = "en/" if any((repo / "en").rglob("*.mdx")) else ""
    PREFIXES = [EN] + [lang + "/" for lang in LANGS]
    eng = repo / EN  # the English pages
    # A codebase folder is 8.4 once it drops its mysql- prefix. It counts only
    # when it holds pages: the old mysql-8.4/ folder keeps schema .json files.
    numbers = [c.removeprefix("mysql-") for c in CODEBASES]
    CODEBASES = [n if any((eng / n).rglob("*.mdx")) else f"mysql-{n}" for n in numbers]
    LABEL = {c: f"MySQL {n}" for c, n in zip(CODEBASES, numbers)}
    docs_path = repo / "docs.json"
    raw = docs_path.read_text()
    docs = json.loads(raw)
    shared = shared_pages(docs)
    codebases = [c for c in CODEBASES if (eng / c / "stable").is_dir()]

    # ----------------------------------------------------------- checks --
    problems = []
    for c in codebases:
        if (eng / c / old).exists():
            problems.append(f"{EN}{c}/{old} already exists")
        dev_names = {p.relative_to(eng / c / "dev") for p in (eng / c / "dev").rglob("*.mdx")}
        for p in (eng / c / "stable").rglob("*.mdx"):
            if p.relative_to(eng / c / "stable") not in dev_names:
                problems.append(f"{EN}{c}/stable/{p.relative_to(eng / c / 'stable')} has no dev page")
    for address in shared:
        for prefix in PREFIXES:
            f = repo / (prefix + address + ".mdx")
            if f.exists() and f"{new}-dev" in strip_notes(f.read_text(), new):
                problems.append(f"{prefix}{address}.mdx: '{new}-dev' appears outside an <Info> note")
    for c in codebases:
        server_names = {str(p.relative_to(eng / c / "stable"))[:-4] for p in (eng / c / "stable").rglob("*.mdx")}
        for address, name in shared.items():
            if name in server_names:
                problems.append(f"archive name {name} is both a {c} server page and the shared page {address}")
    flat = list(shared.values())
    for name in sorted({n for n in flat if flat.count(n) > 1}):
        problems.append(f"two shared pages would both be archived as {name}")
    labels = json.dumps(docs, ensure_ascii=False)
    for c in codebases:
        if f'"{LABEL[c]} · {new}-dev"' not in labels:
            problems.append(f"menu group '{LABEL[c]} · {new}-dev' not found")
    if f"| {new}-dev |" not in (eng / "dev-releases.mdx").read_text():
        problems.append(f"dev-releases.mdx has no row '| {new}-dev |'")
    if "|---|---|---|\n" not in (eng / "past-releases.mdx").read_text():
        problems.append("past-releases.mdx has no table")
    if problems:
        sys.exit("stopped:\n  " + "\n  ".join(problems))

    report = []

    # ---------------------------------------------------------- archive --
    for c in codebases:
        archive_map = {}
        for prefix in PREFIXES:
            for address, name in shared.items():
                archive_map[prefix + address] = f"{prefix}{c}/{old}/{name}"
                if address == "extensions/catalog":
                    # /extensions redirects to the catalog; archive links to it too
                    archive_map[prefix + "extensions"] = f"{prefix}{c}/{old}/{name}"
            archive_map[f"{prefix}{c}/stable"] = f"{prefix}{c}/{old}"
        stable_link = re.compile(r"(?<![\w/.-])/((?:(?:en|ja|ko|zh|pt-BR)/)?)" + re.escape(c) + r"/stable/")
        shared_link = link_pattern(archive_map)
        # The shared pages link to MySQL 8.4 server pages. In another
        # codebase's archive, those links go to that codebase's own page.
        others = [o for o in CODEBASES if o != c]
        other_link = re.compile(r"(?<![\w/.-])/((?:(?:en|ja|ko|zh|pt-BR)/)?)(" + "|".join(re.escape(o) for o in others)
                                + r")/stable/([a-z0-9/-]+)" + END)

        def to_own(m):
            if (eng / c / "stable" / (m.group(3) + ".mdx")).exists():
                return f"/{m.group(1)}{c}/{old}/{m.group(3)}"
            return m.group(0)

        def freeze(text):
            text = strip_notes(text, new)
            # The schema a manifest names by its GitHub address is archived
            # beside the stable one, so the archive names the frozen copy.
            text = SCHEMA_LINK.sub(lambda m: f"{m.group(1)}/{old}/manifest.json.schema.json", text)
            text = stable_link.sub(lambda m: f"/{m.group(1)}{c}/{old}/", text)
            text = other_link.sub(to_own, text)
            return shared_link.sub(lambda m: "/" + archive_map[m.group(1)], text)

        copied = 0
        for prefix in PREFIXES:
            src_dir = repo / (prefix + c) / "stable"
            if src_dir.is_dir():
                for f in src_dir.rglob("*"):
                    if f.is_dir():
                        continue
                    dst = repo / (prefix + c) / old / f.relative_to(src_dir)
                    copied += 1
                    if not dry:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        if f.suffix == ".mdx":
                            dst.write_text(freeze(f.read_text()))
                        else:
                            shutil.copy2(f, dst)
            for address, name in shared.items():
                f = repo / (prefix + address + ".mdx")
                if f.exists():
                    dst = repo / (prefix + c) / old / (name + ".mdx")
                    copied += 1
                    if not dry:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        dst.write_text(freeze(f.read_text()))
        # The schema files stay in the old mysql-<n>/ folders, because extension
        # manifests name them by their GitHub address. Archive them there too.
        legacy = "mysql-" + c.removeprefix("mysql-")
        if legacy != c:
            for prefix in [""] + [lang + "/" for lang in LANGS]:
                src_dir = repo / (prefix + legacy) / "stable"
                if src_dir.is_dir():
                    for f in src_dir.rglob("*"):
                        if f.is_file() and f.suffix != ".mdx":
                            dst = repo / (prefix + legacy) / old / f.relative_to(src_dir)
                            copied += 1
                            if not dry:
                                dst.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(f, dst)
        report.append(f"archive {c}/{old}: {copied} files")
        if not dry:
            subprocess.run([sys.executable, str(repo / "scripts" / "noindex-version.py"), old,
                            "--product", c, "--repo", str(repo)], check=True, capture_output=True)

        # Past releases menu: newest first, right after the index page.
        group = archive_group(docs, c, old, shared)
        past = [i for i in tab(docs, "Server")["menu"] if i["item"] == "Past releases"][0]
        pages = past["groups"][0]["pages"]
        position = 1 + sum(1 for p in pages[1:] if isinstance(p, dict) and p["group"].endswith(f"· {old}"))
        pages.insert(position, group)

    # ---------------------------------------------------------- promote --
    for c in codebases:
        stable, dev = eng / c / "stable", eng / c / "dev"
        report.append(f"promote {c}/dev -> {c}/stable, new {c}/dev from stable")
        if dry:
            continue
        shutil.rmtree(stable)
        shutil.copytree(dev, stable)
        for f in stable.rglob("*.mdx"):
            f.write_text(f.read_text().replace(f"/{c}/dev/", f"/{c}/stable/"))
        shutil.rmtree(dev)
        shutil.copytree(stable, dev)
        for f in dev.rglob("*.mdx"):
            f.write_text(f.read_text().replace(f"/{c}/stable/", f"/{c}/dev/"))
        # The schema files in the old mysql-<n>/ folders follow dev to stable,
        # as they did when they lived beside the pages.
        legacy = "mysql-" + c.removeprefix("mysql-")
        if legacy != c:
            for prefix in [""] + [lang + "/" for lang in LANGS]:
                ldev, lstable = repo / (prefix + legacy) / "dev", repo / (prefix + legacy) / "stable"
                if ldev.is_dir():
                    for f in ldev.rglob("*"):
                        if f.is_file() and f.suffix != ".mdx":
                            dst = lstable / f.relative_to(ldev)
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(f, dst)

    # A server page that is new in dev joins the stable menu, in the group of
    # the same name.
    server = tab(docs, "Server")
    items = {i["item"]: i for i in server["menu"]}
    listed = set(pages_in(server))
    dev_item = items.get("Dev releases")
    for c in codebases:
        if dev_item is None or LABEL[c] not in items:
            continue
        dev_group = [g for g in pages_in_groups(dev_item) if g.get("group", "").startswith(f"{LABEL[c]} · ")]
        for group in dev_group:
            for sub in [group] + [x for x in group["pages"] if isinstance(x, dict)]:
                for page in [x for x in sub["pages"] if isinstance(x, str)]:
                    target = page.replace(f"{c}/dev/", f"{c}/stable/", 1)
                    if target in listed:
                        continue
                    homes = [g for g in items[LABEL[c]]["groups"] if g["group"] == sub["group"]] or items[LABEL[c]]["groups"]
                    homes[0]["pages"].append(target)
                    listed.add(target)
                    report.append(f"added {target} to the {LABEL[c]} menu, group {homes[0]['group']}")

    # ------------------------------------------------------------ notes --
    for address in shared:
        for prefix in PREFIXES:
            f = repo / (prefix + address + ".mdx")
            if not f.exists():
                continue
            t = f.read_text()
            for m, body in note_blocks(t, new):
                line = t.count("\n", 0, m.start()) + 2
                report.append(f"note to check: {prefix}{address}.mdx:{line}")
            if not dry:
                f.write_text(unwrap_notes(t, new))

    # ------------------------------------------------ labels and redirects --
    raw_after = json.dumps(docs, indent=2, ensure_ascii=False) + "\n"
    for c in codebases:
        a, b = f"{LABEL[c]} · {new}-dev", f"{LABEL[c]} · {nxt}"
        raw_after = raw_after.replace(f'"{a}"', f'"{b}"')
    docs = json.loads(raw_after)

    redirects = docs.get("redirects", [])
    kept, removed = [], 0
    for r in redirects:
        s = r["source"]
        # [""]: redirects made before English moved under en/ keep bare sources.
        # and older spellings of the codebase folder (mysql-8.4) too.
        if any(s == f"/{p}{n}/{old}" or s.startswith(f"/{p}{n}/{old}/")
               for c in codebases for n in spellings(c) for p in PREFIXES + [""]):
            removed += 1  # the archive now lives there
            continue
        for c in codebases:
            dev = f"/{EN}{c}/dev"
            for pre in [f"/{e}{n}/{new}-dev" for e in ("", EN) for n in spellings(c)]:
                if (s == pre or s.startswith(pre + "/")) and r["destination"].startswith(dev):
                    r = {"source": s, "destination": f"/{EN}{c}/{new}" + r["destination"][len(dev):]}
        kept.append(r)
    added = []
    for c in codebases:
        added.append({"source": f"/{EN}{c}/{new}", "destination": f"/{EN}{c}/stable"})
        for f in sorted((eng / c / ("dev" if dry else "stable")).rglob("*.mdx")):
            slug = str(f.relative_to(eng / c / ("dev" if dry else "stable")))[:-4]
            added.append({"source": f"/{EN}{c}/{new}/{slug}", "destination": f"/{EN}{c}/stable/{slug}"})
        for address, name in shared.items():
            added.append({"source": f"/{EN}{c}/{new}/{name}", "destination": f"/{EN}{address}"})
    for c in codebases:
        for prefix in PREFIXES:
            if (repo / (prefix + c) / old / "introduction.mdx").exists() or (dry and (repo / (prefix + c) / "stable" / "introduction.mdx").exists()):
                for src in (f"/{prefix}{c}/{old}", f"/{prefix}{c}/{old}/index"):
                    added.append({"source": src, "destination": f"/{prefix}{c}/{old}/introduction"})
    existing = {r["source"] for r in kept}
    unique = []
    for r in added:
        if r["source"] not in existing:
            existing.add(r["source"])
            unique.append(r)
    added = unique
    docs["redirects"] = added + kept
    report.append(f"redirects: removed {removed}, added {len(added)}")

    for name, old_row, new_row in (
        ("dev-releases.mdx", f"| {new}-dev |", f"| {nxt} |"),
    ):
        p = eng / name
        t = p.read_text()
        t = t.replace(old_row, new_row).replace(f"{new}-dev", nxt)
        if not dry:
            p.write_text(t)
    past_page = eng / "past-releases.mdx"
    t = past_page.read_text()
    links = []
    for c in codebases:
        group = [g for g in [i for i in tab(docs, "Server")["menu"] if i["item"] == "Past releases"][0]["groups"][0]["pages"]
                 if isinstance(g, dict) and g["group"] == f"{LABEL[c]} · {old}"][0]
        home = [p for p in pages_in(group) if p.startswith(f"{EN}{c}/{old}/") and p != f"{EN}{c}/{old}/version-policy"][0]
        links.append(f"[Docs](/{home})")
    row = f"| {old} | " + " | ".join(links) + " |\n"
    marker = "|---|---|---|\n"
    t = t.replace(marker, marker + row, 1)
    if not dry:
        past_page.write_text(t)
        docs_path.write_text(json.dumps(docs, indent=2, ensure_ascii=False) + "\n")

    # ------------------------------------------------- manual follow-ups --
    for c in codebases:
        for prefix in PREFIXES:
            d = repo / (prefix + c) / ("dev" if dry else "stable")
            if d.is_dir():
                for f in sorted(d.rglob("*.mdx")):
                    for i, line in enumerate(f.read_text().splitlines(), 1):
                        if re.search(r"(?<![\d.])" + re.escape(old) + r"(?![\d])", line):
                            report.append(f"names {old}: {f.relative_to(repo)}:{i}")
                        if f"{new}-dev" in line:
                            report.append(f"stable still says {new}-dev: {f.relative_to(repo)}:{i}")
            d = repo / (prefix + c) / "dev"
            if d.is_dir() and not dry:
                for f in sorted(d.rglob("*.mdx")):
                    for i, line in enumerate(f.read_text().splitlines(), 1):
                        if re.search(r"(?<![\d.])" + re.escape(new) + r"(?![\d-])", line) or f"{new}-dev" in line:
                            report.append(f"dev should say {nxt}: {f.relative_to(repo)}:{i}")

    print(("[dry run] " if dry else "") + f"cut {old} -> {new}, dev becomes {nxt}")
    for line in report:
        print("  " + line)


if __name__ == "__main__":
    main()
