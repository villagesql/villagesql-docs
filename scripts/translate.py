#!/usr/bin/env python3
"""
VillageSQL docs translation script.

Translates stable-version MDX files into a target language using local Qwen via Ollama.
Run as part of the docs shuffle when cutting a new stable release.

Usage:
    python scripts/translate.py --language ja
    python scripts/translate.py --language ko --model qwen3:30b
    python scripts/translate.py --language zh --dry-run
    python scripts/translate.py --language ja --file guides/uuids.mdx
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DOCS_ROOT = Path(__file__).parent.parent
OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3"

LANGUAGES = {
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese (Simplified)",
}


# ---------------------------------------------------------------------------
# Ollama helpers
# ---------------------------------------------------------------------------

def ollama_generate(model: str, prompt: str) -> str:
    """Stream a generate request and return the full response text."""
    data = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.1},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    parts: list[str] = []
    # Each streamed line is a JSON object; read with a per-chunk timeout
    with urllib.request.urlopen(req, timeout=120) as resp:
        for line in resp:
            chunk = json.loads(line)
            parts.append(chunk.get("response", ""))
            if chunk.get("done"):
                break
    return "".join(parts)


def ollama_post(endpoint: str, payload: dict, timeout: int = 300) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}{endpoint}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def check_ollama(model: str):
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as resp:
            data = json.loads(resp.read())
            available = [m["name"] for m in data.get("models", [])]
            base = model.split(":")[0]
            if not any(m.startswith(base) for m in available):
                print(f"ERROR: Model '{model}' not found in Ollama.")
                print(f"Available: {', '.join(available) or 'none'}")
                print(f"Pull with: ollama pull {model}")
                sys.exit(1)
    except urllib.error.URLError:
        print("ERROR: Ollama is not running. Start it with: ollama serve")
        sys.exit(1)


# ---------------------------------------------------------------------------
# docs.json helpers
# ---------------------------------------------------------------------------

def get_stable_info() -> tuple[str, dict]:
    """Return (version_number, english_nav_entry) for the default stable version."""
    config = json.loads((DOCS_ROOT / "docs.json").read_text())
    for product in config["navigation"]["products"]:
        if "MySQL 8.4" in product["product"]:
            for version in product["versions"]:
                if version.get("default"):
                    ver_str = version["version"]
                    match = re.search(r"\(([^)]+)\)", ver_str)
                    ver_num = match.group(1) if match else ver_str
                    for lang_entry in version.get("languages", []):
                        if lang_entry["language"] == "en":
                            return ver_num, lang_entry
    raise RuntimeError("Could not find stable English navigation in docs.json")


def collect_files(en_nav: dict, include_guides: bool = True) -> list[Path]:
    """Return deduplicated list of source MDX paths referenced by the English nav."""
    seen: set[Path] = set()
    result: list[Path] = []

    def walk(obj):
        if isinstance(obj, str):
            if not include_guides and obj.startswith("guides/"):
                return
            p = DOCS_ROOT / (obj + ".mdx")
            if p.exists() and p not in seen:
                seen.add(p)
                result.append(p)
        elif isinstance(obj, dict):
            if not include_guides and obj.get("group") == "Guides":
                return
            for page in obj.get("pages", []):
                walk(page)
            if "root" in obj:
                if not include_guides and obj["root"].startswith("guides/"):
                    return
                p = DOCS_ROOT / (obj["root"] + ".mdx")
                if p.exists() and p not in seen:
                    seen.add(p)
                    result.append(p)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(en_nav.get("groups", []))
    return result


def make_translated_nav(en_nav: dict, lang: str, include_guides: bool = True) -> dict:
    """Build the translated navigation entry: same structure, paths prefixed with lang/."""

    def prefix(obj):
        if isinstance(obj, str):
            return f"{lang}/{obj}"
        elif isinstance(obj, list):
            return [prefix(item) for item in obj]
        elif isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if k == "default":
                    continue  # only en is default
                elif k in ("pages", "groups"):
                    out[k] = prefix(v)
                elif k == "root":
                    out[k] = f"{lang}/{v}"
                else:
                    out[k] = v
            return out
        return obj

    groups = en_nav.get("groups", [])
    if not include_guides:
        groups = [g for g in groups if g.get("group") != "Guides"]
    return {"language": lang, "groups": prefix(groups)}


def update_docs_json(lang: str, translated_nav: dict):
    """Replace the stub language entry in docs.json with the full translated nav."""
    docs_json_path = DOCS_ROOT / "docs.json"
    config = json.loads(docs_json_path.read_text())

    for product in config["navigation"]["products"]:
        if "MySQL 8.4" in product["product"]:
            for version in product["versions"]:
                if version.get("default"):
                    langs = version.get("languages", [])
                    for i, entry in enumerate(langs):
                        if entry["language"] == lang:
                            langs[i] = translated_nav
                            break

    docs_json_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------

TRANSLATION_PROMPT = """\
Translate the following MDX documentation from English to {lang_name}.

Rules:
- Preserve ALL MDX and Markdown syntax exactly: component tags, HTML elements, \
headings, lists, links, tables, callout blocks
- Inline code in backticks (` ... `) must not be translated — preserve exactly
- In YAML frontmatter (between --- lines): translate ONLY the values of "title" and \
"description". Leave all other keys and values unchanged exactly as written
- Never translate URLs, hrefs, file paths, or image src values
- Never translate these terms regardless of context:
  VillageSQL, VEF, VEB, VDF, Victionary, InnoDB, MTR, MySQL, SQL, GitHub, Discord
- Never translate any term matching the pattern vsql_* or vsql-* (e.g. vsql_ai, vsql-crypto)
- Preserve UPPER_CASE identifiers, snake_case identifiers, and camelCase identifiers \
that are clearly technical terms rather than {lang_name} words
- Preserve all HTML comments exactly as-is — do not translate or remove them
- Preserve all blank lines between sections exactly
- Output ONLY the translated content — no explanation, no commentary, no code fences \
wrapping the output

{content}"""

# HTML comment placeholders — models reliably preserve HTML markup in MDX
_FENCE_PH = "<!-- CODEBLOCK_{i} -->"
_FENCE_RE = re.compile(r"<!-- CODEBLOCK_(\d+) -->")

CHUNK_LINE_LIMIT = 500


def _extract_code(content: str) -> tuple[str, list[str]]:
    """Replace fenced code blocks with HTML comment placeholders."""
    blocks: list[str] = []

    def replacer(m: re.Match) -> str:
        blocks.append(m.group(0))
        return _FENCE_PH.format(i=len(blocks) - 1)

    text = re.sub(r"```[^\n]*\n[\s\S]*?```", replacer, content)
    return text, blocks


def _restore_code(content: str, blocks: list[str]) -> str:
    return _FENCE_RE.sub(lambda m: blocks[int(m.group(1))], content)


def _call_model(text: str, lang: str, lang_name: str, model: str) -> str:
    prompt = TRANSLATION_PROMPT.format(lang_name=lang_name, content=text)
    result = ollama_generate(model, prompt).strip()
    result = re.sub(r"<think>.*?</think>\s*", "", result, flags=re.DOTALL)
    result = re.sub(r"\s*/?think\s*$", "", result)
    result = re.sub(r"^```(?:mdx|markdown)?\n", "", result)
    result = re.sub(r"\n```$", "", result)
    return result


def translate_file(content: str, lang: str, lang_name: str, model: str) -> str:
    content_no_code, blocks = _extract_code(content)
    lines = content_no_code.splitlines(keepends=True)

    if len(lines) <= CHUNK_LINE_LIMIT:
        translated = _call_model(content_no_code, lang, lang_name, model)
    else:
        chunks: list[str] = []
        current: list[str] = []
        for line in lines:
            current.append(line)
            if len(current) >= CHUNK_LINE_LIMIT and line.strip() == "":
                chunks.append("".join(current))
                current = []
        if current:
            chunks.append("".join(current))
        translated = "\n".join(_call_model(c, lang, lang_name, model) for c in chunks)

    # Validate placeholders survived
    for i in range(len(blocks)):
        if _FENCE_PH.format(i=i) not in translated:
            raise RuntimeError(f"Code block placeholder {i} dropped — re-run this file.")

    return _restore_code(translated, blocks)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git(*args: str, check=True, capture=True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(DOCS_ROOT), *args],
        check=check,
        capture_output=capture,
        text=True,
    )


def create_branch(lang: str, version: str) -> str:
    branch = f"translations/{lang}-{version}"
    git("fetch", "origin")
    git("checkout", "-b", branch, "origin/main")
    return branch


def git_add(path: Path):
    git("add", str(path))


def git_commit(msg: str):
    git("commit", "-m", msg, capture=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Translate VillageSQL stable docs")
    parser.add_argument(
        "--language", "-l", required=True, choices=list(LANGUAGES),
        metavar="LANG", help="Target language: ja, ko, zh",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Ollama model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List files that would be translated without running",
    )
    parser.add_argument(
        "--file", "-f", metavar="PATH",
        help="Translate a single file and print to stdout (for spot-checking)",
    )
    parser.add_argument(
        "--no-branch", action="store_true",
        help="Skip branch creation and commit to the current branch",
    )
    parser.add_argument(
        "--no-guides", action="store_true",
        help="Skip guide files and exclude Guides from the translated nav",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip files that already exist on disk (resume an interrupted run)",
    )
    args = parser.parse_args()

    lang = args.language
    lang_name = LANGUAGES[lang]

    if not args.dry_run and not args.file:
        check_ollama(args.model)

    version, en_nav = get_stable_info()
    print(f"Stable version : {version}")
    print(f"Target language: {lang_name} ({lang})")
    print(f"Model          : {args.model}")

    # Single-file spot-check mode
    if args.file:
        path = DOCS_ROOT / args.file
        if not path.exists():
            print(f"ERROR: {path} not found")
            sys.exit(1)
        content = path.read_text(encoding="utf-8")
        result = translate_file(content, lang, lang_name, args.model)
        print(result)
        return

    include_guides = not args.no_guides
    files = collect_files(en_nav, include_guides=include_guides)
    print(f"Files          : {len(files)}{' (guides excluded)' if not include_guides else ''}\n")

    if args.dry_run:
        for f in files:
            rel = f.relative_to(DOCS_ROOT)
            print(f"  {rel}  →  {lang}/{rel}")
        return

    if args.no_branch:
        branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        print(f"Branch: {branch} (existing)\n")
    else:
        branch = create_branch(lang, version)
        print(f"Branch: {branch}\n")

    errors: list[tuple[Path, str]] = []
    translated_count = 0

    for i, source_path in enumerate(files, 1):
        rel = source_path.relative_to(DOCS_ROOT)
        output_path = DOCS_ROOT / lang / rel
        label = f"[{i:>3}/{len(files)}] {rel}"
        if args.resume and output_path.exists():
            print(f"{label} ... skipped")
            translated_count += 1
            continue

        print(label, end=" ... ", flush=True)

        try:
            content = source_path.read_text(encoding="utf-8")
            translated = translate_file(content, lang, lang_name, args.model)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(translated, encoding="utf-8")
            git_add(output_path)
            git_commit(f"{lang}: {rel}")
            translated_count += 1
            print("done")
        except Exception as e:
            errors.append((rel, str(e)))
            print(f"FAILED: {e}")

    # Update docs.json navigation
    translated_nav = make_translated_nav(en_nav, lang, include_guides=include_guides)
    update_docs_json(lang, translated_nav)
    git_add(DOCS_ROOT / "docs.json")
    result = git("status", "--porcelain", "docs.json")
    if result.stdout.strip():
        git_commit(f"Update docs.json nav for {lang} stable {version}")

    print(f"\n{'─' * 55}")
    print(f"Translated : {translated_count}/{len(files)} files")
    if errors:
        print(f"Errors     : {len(errors)}")
        for p, err in errors:
            print(f"  {p}: {err}")
    print(f"Branch     : {branch}")
    print("Review the branch, then open a PR when ready.")


if __name__ == "__main__":
    main()
