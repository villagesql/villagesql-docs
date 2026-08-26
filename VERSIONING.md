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

The script cuts one product. It defaults to `mysql-8.4`; add
`--product mysql-9.7` to cut that one. Each product is cut on its own release
cadence, and every `docs.json` edit is scoped to the product named, so cutting
one never relabels another.

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

The "Coming Soon" MySQL 8.0 product in `docs.json` uses a plain `Stable`
label. Keep it in sync with that convention. It is a single `index.mdx`
under `mysql-8.0/0.0.1/`, `noindex`ed, pointing readers at the MySQL 8.4
stable slot. MySQL 9.7 was a placeholder of the same shape and is no longer
one — see the next section.

## Adding a MySQL version (built — 9.7)

Built 2026-08-22. This section records the agreed shape that build followed.

**Both server builds shipped in 0.0.6, on 2026-08-25.** The `release/0.0.6`
release carries three tarballs for each codebase, and Docker Hub carries one
image for each codebase and architecture.

**Refer to the branches of record, never a personal branch.** Engineering work
on the two newer codebases happens on `mysql-9.7` and `percona-8.4` in
`villagesql-server`, and those branches keep taking commits. What each release
delivered is marked by a tag instead: `publish/mysql-8.4_0.0.6`,
`publish/mysql-9.7_0.0.6`, `publish/percona-8.4_0.0.6`. A `dbentley/*` or
`adam/*` branch may hold the same commits and is still not the source of truth.

**Every artifact names the codebase and the VillageSQL version, joined by an
underscore** — `mysql-8.4_0.0.6`, `mysql-9.7_0.0.6`, `percona-8.4_0.0.6`. A
running server reports the same string in `@@villagesql_server_version`, and it
is how a reader confirms which codebase they installed.

| Artifact | Pattern |
|---|---|
| Git tag for a shipped release | `publish/<codebase>_<version>` |
| Release tarball | `villagesql-dev-server-<codebase>_<version>-<os>-<arch>.tar.gz` |
| Docker image | `villagesql/server:<codebase>_<version>-<arch>` |

**Every Docker command in the docs names an architecture.** Docker Hub carries
one image per codebase and architecture, and nothing else: no combined tag such
as `mysql-8.4_0.0.6`, and no floating tag such as `stable` or `latest`, both of
which were deleted on 2026-08-25. That is a decision, not a gap (Lee,
2026-08-25) — a combined tag can be added after launch if it proves useful. So
a Docker command must end in `-amd64` or `-arm64`, and the version number is
part of every one of them. Expect to rewrite each Docker command in the docs at
every release until a floating tag exists.

**Model: parallel trees, like the upstream MySQL manual.** Each MySQL version
gets a complete, independently editable doc set under its own product in the
`docs.json` product switcher — `mysql-8.4/` and `mysql-9.7/`. Readers see a
whole 9.7 manual at 9.7 URLs, not a shared tree with the version filed off. Two
near-identical indexed trees are normal for versioned documentation and are not
treated as a duplicate-content problem, the same reasoning that lets the
`stable/` and `dev/` slots both stay indexed.

**Seed 9.7 by copying the dev slot, not stable.** When 9.7 work begins, mirror
`mysql-8.4/dev/` to `mysql-9.7/dev/` and substitute the version tokens. Dev is
English-only, so seeding from dev costs **no translation work at all**;
translation starts only when 9.7 cuts its first stable. Do not seed from
`mysql-8.4/stable/`, which would immediately owe four locale mirrors.

**What actually differs.** Measured against `mysql-8.4/dev/` on 2026-08-17,
excluding in-page self-links, only these pages carry MySQL-version-specific
content:

| Page | What ties it to a MySQL version |
|---|---|
| `index.mdx` | "compatible with MySQL 8.4.10", and the same string in `description` |
| `reference.mdx` | `VERSION()` output examples (`mysql-8.4_0.0.6-dev`); "not part of standard MySQL 8.4 syntax" |
| `source.mdx` | build version string example; the source build's version option |
| `install.mdx` | the install script's version option |
| `quickstart.mdx` | the Docker tag and the one-line install command |
| `create.mdx` | one link to `dev.mysql.com/doc/extending-mysql/8.4/en/...` |

The remaining ~24 pages — the whole C++ and Rust SDK surface, extension
authoring, protocol, testing — contain no MySQL-version reference. They copy
across unchanged and should stay identical until a real difference appears.

**Reconciliation is not built yet.** The plan was for `freshness.py` to report
every page whose 9.7 copy differs from its 8.4 twin after version-token
substitution, as a reminder to update both copies — not a rule forbidding
difference, since a page in the table above is expected to differ every run.
That check does not exist in `vsql-docs-validator/freshness.py` as of
2026-08-23. Until it does, nothing catches a fix landing in one tree and not
the other — three open PRs (#195, #196, #188) did exactly that and had to be
found and patched into the 9.7 tree by hand. Start with the bare report when
building it. Only if that list grows too noisy to read is it worth adding a
per-page "differs on purpose" marker — do not build that machinery up front.

**Version selection is a packaging decision first.** VillageSQL builds three
flavors, each with its own build artifacts, and the install script offers all
three:

| Flavor | Documented in |
|---|---|
| MySQL 8.4 | `mysql-8.4/` |
| MySQL 9.7 | `mysql-9.7/` |
| MySQL 8.4 with Percona changes | `mysql-8.4/dev/percona.mdx` |

**A Percona flavor belongs to a MySQL version, and there will eventually be a
9.7 one.** Today only the 8.4 Percona build exists, so `percona.mdx` starts life
in the 8.4 tree alone. When the 9.7 Percona build ships, it gets its own
`mysql-9.7/dev/percona.mdx` — do not write a single shared Percona page that
tries to cover both, and do not treat Percona's absence from the 9.7 tree as
permanent.

That shapes `install.mdx` and `source.mdx`. Both appear in both trees, and each
lists the flavors that exist for its own MySQL version — three choices in 8.4
today, two in 9.7 until the 9.7 Percona build lands. So both pages carry a real
difference between the trees from the start, and stay on the differs-from-8.4
list permanently.

`percona.mdx` itself stays short: what the branch is, which artifact to install,
what VillageSQL supports, and a link to Percona's own documentation. Do not
document Percona's changes here.

Get the option names from the server team before writing any of these pages.
The page structure follows the flag names.

## Percona branch

Built 2026-08-22. VillageSQL ships a second buildable 8.4 codebase that
integrates Percona's MySQL improvements, on the `percona-8.4` branch.

**Do not document Percona's own changes.** Document that the branch exists, how
to build and install it, and what VillageSQL supports about it. Send every
question about the Percona improvements themselves to Percona's documentation.
This lives in one page, `mysql-8.4/dev/percona.mdx`, linked from
`quickstart.mdx` and `source.mdx`.

**An index of the Percona changes is worth having only if a script generates
it.** A hand-written summary of another project's feature set goes stale in
silence. If the server repo can emit the list — a merge manifest, a tagged
commit range, a build flag list — generate the page and let `freshness.py` fail
when the source moves. If nothing can generate it, link to Percona and stop.
