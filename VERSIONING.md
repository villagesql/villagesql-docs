---
noindex: true
---

# Documentation Versioning Policy

## Model

The VillageSQL version number is **not** in the documentation URL. Content
lives in fixed slots:

- **Current stable** → `mysql-8.4/stable/` (served at
  `villagesql.com/docs/mysql-8.4/stable/...`). Indexed.
- **Development** → `mysql-8.4/dev/`. Indexed and **self-canonical** — no
  cross-canonical to stable, so dev's new features (whether on new pages or
  added to existing ones) stay findable in search. Making the latest features
  findable is a deliberate goal; stable wins the identical mirror pages anyway
  because all internal links, the sitemap, and `llms.txt` point at `/stable/`.
- **Frozen archives** → `mysql-8.4/0.0.4/`, `0.0.3/`, … Each is a snapshot of a
  past release, `noindex`ed, kept reachable at its direct URL.

Because the stable and dev URLs never change, cutting a release **moves no live
URL** — Google indexes one fixed set of stable URLs across all releases, and no
per-release reindexing or mass redirect is needed. This is the whole point of
the slot model. The version number stays visible to readers through the
`docs.json` version-switcher label (e.g. `Stable (0.0.5)`), not the URL.

The current stable version is translated (ja/ko/zh/pt-BR). A version that
shipped translations keeps its translations **and** its language switcher after
it is archived. The dev version and older never-translated versions are
English-only.

## Workflow

**All changes go to the dev slot** (`mysql-8.4/dev/`).

## Cutting a Release

Runbook for promoting dev to stable. The example cuts **stable 0.0.5 → 0.0.6**
and opens **0.0.7-dev**. Substitute versions as needed. **Freeze dev content
before starting** — the promote and translation steps assume it is final.

### 1. Run the shuffle (automated)

```bash
python3 scripts/promote-release.py \
    --old-stable 0.0.5 --new-stable 0.0.6 --new-dev 0.0.7-dev --dry-run
# review the plan, then run for real (drop --dry-run)
python3 scripts/promote-release.py \
    --old-stable 0.0.5 --new-stable 0.0.6 --new-dev 0.0.7-dev
```

This performs, in order:
- **Snapshot** `mysql-8.4/stable/` (and each locale mirror) → `mysql-8.4/0.0.5/`,
  rewriting the archive's self-links `stable/` → `0.0.5/` so the frozen copy
  refers to its own version.
- **Noindex** the new `0.0.5` archive (all locales, via `noindex-version.py`).
- **Promote** `mysql-8.4/dev/` → `mysql-8.4/stable/` (English): rewrite `dev/` →
  `stable/` links.
- **Scaffold** a fresh `mysql-8.4/dev/` from the new stable. Dev is
  self-canonical (no canonical stamping), so its new features stay findable.
- **Insert** the archived version entry into `docs.json` `versions` (the old
  stable entry relabeled to the bare number `0.0.5`, repointed to
  `mysql-8.4/0.0.5/...`, keeping its `languages` block so the archived-but-
  translated switcher survives), then **bump** the two labels: `Stable (0.0.5)`
  → `Stable (0.0.6)` and `Development (0.0.6-dev)` → `Development (0.0.7-dev)`.
- **Update redirects** so every version number keeps resolving: drop the
  `0.0.5 → /stable/` redirects (so the freshly-frozen `0.0.5` archive is
  reachable, not shadowed), repoint the `0.0.6-dev` redirects to `0.0.6` (old
  dev links track what shipped), and add `0.0.6 → /stable/` (the new current
  stable resolves at its number too). `docs.json` is re-validated before write.

The stable and dev *slot* URLs never move — the only redirect churn is on the
version *numbers*, and it keeps them all resolving: the current stable's number
bounces to `/stable/`, and a superseded number becomes its own frozen archive.
(`gen-redirects.py` is only for one-off structural URL moves.)

### 2. Re-translate the new stable into ja/ko/zh/pt-BR

Only `mysql-8.4/` and `extensions/` are translated per locale — **not**
`guides/`. Output overwrites `ja/mysql-8.4/stable/`, `ko/...`, `zh/...`,
`pt-BR/...`.

- **Translator: Opus via Claude Code.** Anthropic API keys are disabled for this
  workspace, so `translate.py --model opus` can't authenticate here — drive the
  Opus translation through a Claude Code session (a Workflow fanning over the
  files). `translate.py` reads the stable slot from `docs.json` automatically.
- **Quality judge: Gemini (`agy`)** — native-language FIX/LEAVE pass. Do not use
  a weaker model to judge a stronger one.
- **Code blocks + placeholders:** never send fenced code to the model — extract
  before, restore after; a dropped placeholder is a hard failure (re-run).
- **Link prefixing:** in a `<lang>` page, prefix in-content links to *translated*
  sections: `](/mysql-8.4/...)` → `](/<lang>/mysql-8.4/...)` and
  `](/extensions/...)` → `](/<lang>/extensions/...)`. **Leave `](/guides/...)`
  bare** — guides aren't translated. Add `{#english-slug}` custom ids to
  link-target headings so English-slug anchors keep resolving.
- Branch convention: `adam/translations-0.0.6`, one squashed commit.

### 3. Update version-number prose (not URLs)

The slots are fixed, so hrefs no longer change at a cut. Only the version-number
*text* can go stale — sweep for it and update or make it version-agnostic:
- `index.mdx`, `snippets/villagesql-banner.mdx`, `extensions/index.mdx`.
- **Do NOT** bump the "requires VillageSQL 0.0.4 or later" lines — that is a
  minimum-version floor (Protocol 2 landed in 0.0.4), not the current version.

### 4. Cross-repo + tooling (outside this repo)

- **`villagesql-website`**: bump the display version in `src/_data/site.js`
  (`docsVersion`). The docs links point at the fixed `/stable/` slot, so no
  per-cut link edits are needed. Deploy only **after** the new docs are live.
- **`vsql-docs-validator/freshness.py`** (on disk, not a git repo — edit the
  standalone copy, not the `claude-config` backup): add the newly-archived
  number (`0.0.5`) to `_ARCHIVED_VERSIONS`. The `dev/`/`stable/` slot prefixes
  are fixed, so — unlike the old numbered model — they no longer need remapping
  every cut.
- **`vsql-extension-template` and `vsql-extension-template-rust`**: bump the
  pinned `villagesql-version` in each repo's scaffold CI workflow
  (`.github/workflows/ci.yml` and `_github/workflows/ci.yml` respectively) to
  the new stable. The scaffold pins a fixed release rather than tracking the
  newest one, so an extension author's build never changes underneath them —
  which means nothing bumps it but this step.

### 5. All future changes go to the dev slot (`mysql-8.4/dev/`).

## Archive Policy

- Keep **10 versions** in the switcher dropdown.
- When adding version 11, remove the oldest version entry from `docs.json` (but
  keep its files). Archived versions remain reachable via direct URL, e.g.
  `villagesql.com/docs/mysql-8.4/0.0.1/quickstart`.

## Placeholder products

The "Coming Soon" MySQL 8.0 and 9.7 products in `docs.json` use a plain `Stable`
label. Keep them in sync with that convention.
