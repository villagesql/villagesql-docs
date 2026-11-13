---
noindex: true
---

# Documentation Versioning Policy

## Layout

English pages live under `en/`, and each translation lives under its language
code (`ja/`, `ko/`, `zh/`, `pt-BR/`) with the same paths. The home page,
`index.mdx`, is the only English page at the root. Every address keeps
working when a release is cut, so search engines see one fixed set of
addresses.

There are two kinds of page:

- **Shared pages** exist once for every release: the extension pages
  (`en/extensions/`, `en/extensions/build/`), the SDK references
  (`en/sdk/cpp/`, `en/sdk/rust/`), `en/version-policy.mdx`, the Quickstart,
  the Guides, and the Tutorial. Their text describes the current release.
- **Server pages** have a copy for each server and release slot:
  `en/8.4/stable/`, `en/8.4/dev/`, `en/9.7/stable/`, and `en/9.7/dev/`. They
  cover installing, building, and running the server. Past releases are
  frozen copies at `en/8.4/0.0.6/` and so on, marked `noindex`.

A change that exists only in the next release goes on the shared page as a
note, so readers of the current release are not misled:

```mdx
<Info>
**Changed in 0.0.8-dev.** What is different in the next release.
</Info>
```

MySQL 8.4 and MySQL 9.7 work the same way by design. When a real difference
exists, the shared page marks it with a `**MySQL 9.7:**` note, as the managing
page does for the Docker image name. Links to Oracle's MySQL manual point at
the 8.4 edition.

Translated pages cover the shared pages, the Guides and the Tutorial
included, and the stable server pages. The dev pages are English only. A
page with no translation in a language is left out of that language's menu.

The `manifest.json.schema.json` files stay at their old paths
(`mysql-8.4/stable/`, `mysql-8.4/0.0.6/`, and so on), because extension
manifests name them by their GitHub address.

## Where a change goes

- **A change in the released software, or a fix to wrong text:** edit the
  text of the shared page, or the stable server page.
- **A change that exists only on `main`:** edit the dev server page, or add a
  `Changed in <next>-dev` note to the shared page.
- **A change in an extension:** an extension has its own version, and a
  release ships the version that was bundled when it was built (0.0.7 shipped
  `vsql_trgm` 0.0.3 after vsql-trgm had tagged 0.0.4). Find the shipped version
  in the release tarball's `lib/veb/<name>.veb` manifest, and check the change
  against that version's tag in the extension repo with
  `git merge-base --is-ancestor <sha> <version>`. A change in the shipped
  version goes in the page text; a newer change is a `Changed in <next>-dev`
  note. The docs agent runs `release-ext-versions` for the first step.

## Cutting a release

The example cuts stable 0.0.7 to 0.0.8 and opens 0.0.9-dev. Freeze the
English text before you start, because the translation step assumes it is
final.

### 1. Run the cut

```bash
python3 scripts/cut-release.py --old 0.0.7 --new 0.0.8 --next 0.0.9-dev --repo . --dry-run
# read the plan, then run it again without --dry-run
```

The script does these steps, in order:

- **Archive.** It copies each server's stable pages to `en/8.4/0.0.7/` and
  `en/9.7/0.0.7/`, with the shared pages beside them, and does the same for
  each translation. The copies leave out the `0.0.8-dev` notes, point their
  links at the archive, get `noindex`, and get a group in the Past releases
  menu.
- **Promote.** Each server's dev pages replace its stable pages, and a new
  dev copy starts from the new stable.
- **Notes.** Every `Changed in 0.0.8-dev` note on a shared page becomes normal
  page text. The script lists each one; read the sentences around it.
- **Labels and redirects.** The menu labels, `dev-releases.mdx`, and
  `past-releases.mdx` name the new numbers, and every version number keeps
  resolving.
- **Leftovers.** It lists the server pages that still name the old release,
  for you to update.

### 2. Translate what changed

Translate into ja, ko, zh, and pt-BR only what changed in the English pages
since the last cut. Keep every translated sentence whose English did not
change, translate new and changed text, and delete text that English removed.
A new page is translated in full.

- **Translator: Fable, from a Claude Code session,** one helper per language.
- **Code blocks are copied from English,** never translated. Every code block
  must match English, in the same order, with the same headings, front-matter
  keys, and link targets.
- **Links:** in a translated page, a link to a translated page carries the
  language prefix, such as `](/ja/extensions/install)`. A link to a
  page with no translation, such as a dev page, keeps its `/en/` address.
- **Headings that links point at** get the English slug as a custom id, such
  as `## 見出し {#english-slug}`, so English anchors keep working.
- **Mechanical check:**
  `python3 ~/scripts/check_translations.py --docs . --version stable --langs ja,ko,zh,pt-BR`.
  It exits 1 when it finds no pages.
- **Review: Gemini (`agy`),** one call per changed page, comparing the
  translation with English. A Fable helper per language then checks each
  finding against English and applies the correct ones. English is the
  authority, not the reviewer.

Then make the 9.7 server-page translations from the 8.4 ones, with no second
translation run:

```bash
python3 scripts/mirror-locales.py --from 8.4 --to 9.7 --slot stable
# translate the lines it lists by hand, then:
python3 scripts/mirror-locales.py --from 8.4 --to 9.7 --slot stable --check
```

`mirror-locales.py` swaps the version tokens and takes each code block from
the English 9.7 page. It lists the English lines whose 9.7 wording is not a
token swap: in each translated page, remove the translation of each `-` line
and translate each `+` line. `--check` exits 0 only when the code spans,
links, and code-block positions match English. Do not run it again without
`--check` after the hand edits, because a full run writes the pages again.

Last, rebuild the translated menus from the English menu:

```bash
python3 scripts/build-translated-menus.py .
```

### 3. Update version numbers in prose

Addresses do not change at a cut, but text that names the current version can
go stale. Check `index.mdx`, `snippets/villagesql-banner.mdx`, and the catalog
introduction in `snippets/extensions-en.mdx`. Leave a sentence such as
"requires VillageSQL 0.0.4 or later" alone: it states a minimum version, not
the current one.

### 4. Other repositories

- **`villagesql-website`:** update the version shown on the site
  (`docsVersion` in `src/_data/site.js`). Deploy it after the new docs are
  live.
- **`vsql-extension-template` and `vsql-extension-template-rust`:** update the
  pinned `villagesql-version` in each repository's CI workflows: both
  `.github/workflows/ci.yml` and `_github/workflows/ci.yml` in the C++
  template, and `_github/workflows/ci.yml` in the Rust template. The scaffold
  pins a release so that an extension author's build does not change under
  them, so only this step moves it.

## Server builds and their names

VillageSQL builds three codebases, and the install script offers all three:
MySQL 8.4, Percona Server 8.4, and MySQL 9.7. The Percona build tracks MySQL
8.4 only, so its pages (`percona.mdx`, `install-percona.mdx`, and
`source-percona.mdx`) live in the 8.4 server pages. Document that the Percona
build exists, how to install and build it, and what VillageSQL supports about
it. Send questions about Percona's own changes to Percona's documentation.

Every artifact names the codebase and the VillageSQL version, joined by an
underscore, such as `mysql-8.4_0.0.7` or `percona-8.4_0.0.7`. A running server
reports the same string in `@@villagesql_server_version`.

| Artifact | Name |
|---|---|
| Git tag for a release | `publish/<codebase>_<version>` |
| Release tarball | `villagesql-dev-server-<codebase>_<version>-<os>-<arch>.tar.gz` |
| Docker image | `villagesql/server:<codebase>_<version>`, and `villagesql/server:<codebase>_latest` |

`villagesql/server:latest` is the current MySQL 8.4 release. Refer to the
release tags, not to a branch: work continues on the `mysql-9.7` and
`percona-8.4` branches after each release.
