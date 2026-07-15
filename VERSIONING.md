---
noindex: true
---

# Documentation Versioning Policy

## Workflow

**All changes go to the dev branch** (e.g., `mysql-8.4/0.0.6-dev/`).

The current stable version is translated (ja/ko/zh). A version that has shipped
translations keeps its translations **and** its language switcher after it is
archived (see step 3). The dev version and older versions that were never
translated are English-only.

### Cutting a Release

Runbook for promoting the dev version to stable. Example below cuts
`0.0.5-dev` → stable `0.0.5` and opens `0.0.6-dev`. Substitute versions as
needed. **Freeze dev content before starting** — steps 1 and 8 (rename and
translation) both assume the content is final.

1. **Rename dev to version number**
   ```bash
   mv mysql-8.4/0.0.5-dev mysql-8.4/0.0.5
   ```

2. **Update `docs.json` version labels** (MySQL 8.4 product)
   - Rename `Development (0.0.5-dev)` → `Stable (0.0.5)` (no `-alpha`).
   - Add `"default": true` to the new stable (0.0.5).
   - Remove `"default": true` from the old stable (0.0.4).
   - Change the old stable's label to a bare version number: `Stable (0.0.4)`
     → `0.0.4`.

3. **Give the new stable its own `languages` block; keep the old one's** (i18n)
   - The `languages` array (en/ja/ko/zh) lives **inside a version entry**.
     Build a fresh block for the new stable (0.0.5) from its English nav — `en`
     plus one entry per locale with `/<lang>/mysql-8.4/0.0.5/...` paths
     (translated navs drop the Guides group). Put `"default": true` on the
     `en` entry only.
   - **Keep the previous stable's `languages` block.** A version that shipped
     translations keeps its switcher after it is archived — only remove the
     entry-level `"default": true` from it (that moves to the new stable). Do
     not strip its `languages` array; the translated files and the switcher
     both stay. (Policy set 2026-07-09: archived-but-translated versions keep
     their switcher; they are still noindexed per step 4 for SEO.)
   - Versions that were never translated (e.g. 0.0.1–0.0.3) remain English-only.

4. **Noindex the old stable**
   ```bash
   python3 scripts/noindex-version.py 0.0.4          # add --dry-run first
   ```
   Adds `noindex: true` to the frontmatter of every `.mdx` in
   `mysql-8.4/0.0.4/` **and its locale mirrors** (`ja/`, `ko/`, `zh/`).
   Idempotent.

5. **Create the new dev branch**
   ```bash
   cp -r mysql-8.4/0.0.5 mysql-8.4/0.0.6-dev
   ```
   - Add a `Development (0.0.6-dev)` entry to `docs.json` (English-only, no
     `languages` block).

6. **Add redirects** for the retired dev URLs
   ```bash
   python3 scripts/gen-redirects.py 0.0.5-dev 0.0.5   # prints JSON to paste
   ```
   Paste the emitted array into the `"redirects"` list in `docs.json`
   (mirrors the existing `0.0.4-dev` → `0.0.4` block). Keep older redirect
   blocks intact.

7. **Update content links to the new stable** (these are hardcoded)
   - `index.mdx` — quickstart card `href` and the "Built-in Extensions"
     sentence ("VillageSQL Server 0.0.5 includes...").
   - `extensions/index.mdx` — the install-script link (`[install script]`).
   - `snippets/villagesql-banner.mdx` — the banner `href`.
   - **Do NOT** bump the "requires VillageSQL 0.0.4 or later" lines in
     `extensions/index.mdx` — that number is a minimum-version floor
     (Protocol 2 landed in 0.0.4), not the current version.

8. **Translate the new stable** into ja/ko/zh. Only `mysql-8.4/` and
   `extensions/` are translated per locale — **not** `guides/`. Output lands
   in `ja/mysql-8.4/0.0.5/`, `ko/...`, `zh/...`.
   - **Translator: Opus via Claude Code (Option A).** Anthropic API keys are
     disabled for this workspace, so `translate.py --model opus` can't
     authenticate. Drive the Opus translation through a Claude Code session at
     cut time (a Workflow fanning over the files), applying the discipline
     below. (`translate.py`'s Opus backend still works for anyone who has an
     API key — it just can't run here.)
   - **Comparison run (optional):** `~/scripts/translate.py --language <lang>
     --model qwen3` (local Ollama) overnight, on its OWN branch — translate.py
     commits into `DOCS_ROOT/<lang>/`, so a second run overwrites the first;
     diff branches to compare.
   - **Quality judge: Gemini (`agy`)** — native-language FIX/LEAVE pass, as in
     the 0.0.4 cycle. Do not use a weaker model to judge a stronger one. agy
     runs as a bash step, not from Python (it prints to the TTY).
   - **Code blocks + placeholders:** never send fenced code to the model —
     extract before, restore after; a dropped placeholder is a hard failure
     (re-run the file). `translate.py` enforces this structurally; Option A
     must replicate it.
   - **Link prefixing (REQUIRED — Mintlify does NOT auto-scope in-content
     links; confirmed against Mintlify's own `/es/` docs, 2026-07-08).** In a
     `<lang>` page, prefix in-content links to *translated* sections only:
     `](/mysql-8.4/...)` → `](/<lang>/mysql-8.4/...)` and
     `](/extensions/...)` → `](/<lang>/extensions/...)` (same for `href="..."`).
     **Leave `](/guides/...)` bare** — guides aren't translated, so a prefixed
     link 404s. Add `{#english-slug}` custom ids to link-target headings so
     English-slug anchors keep resolving.
   - Branch convention: `adam/translations-0.0.5`, one squashed commit.

9. **Update the website stable pointer** (repo: `villagesql-website`) —
   **deploy only after the 0.0.5 docs are live**, or the site links 404.
   - `src/_data/site.js` → `docsVersion: "0.0.5"` (auto-updates ~16 links).
   - `src/llms.txt.njk` — bump the hardcoded **Development Preview** heading
     and its dev URLs (`0.0.5-dev` → `0.0.6-dev`). Leave the "requires
     VillageSQL 0.0.4" extension lines (minimum version, same as step 7).

10. **Update `vsql-docs-validator/freshness.py` version references.** It
    hardcodes version dirs in `_ARCHIVED_VERSIONS`, `_RAW_ABI_PROSE_EXEMPT`,
    the audience-check path prefix, and `REFERENCE_SCHEMA_CHECKS`. Add the
    previous stable (e.g. `0.0.4`) to `_ARCHIVED_VERSIONS`; remap the retired
    dev version (`0.0.5-dev`) to the new dev (`0.0.6-dev`) everywhere else.
    Otherwise `freshness.py --check-docs` crashes on the renamed path. It is
    on disk, not a git repo — edit in place.

11. **All future changes go to the new dev branch** (`mysql-8.4/0.0.6-dev/`).

## Archive Policy

- Keep **10 versions** in the dropdown.
- When adding version 11, remove the oldest from `docs.json` (but keep files).
- Archived versions remain accessible via direct URL, e.g.
  `villagesql.com/docs/mysql-8.4/0.0.1/quickstart`.

## Placeholder products

The "Coming Soon" MySQL 8.0 and 9.7 products in `docs.json` use a plain
`Stable` label (no `-alpha`). Keep them in sync with the no-`-alpha`
convention.

---

Each version is ~132KB. Archived versions stay accessible at direct URLs.
