# VillageSQL Documentation Style Guide

This guide is how we write the VillageSQL docs. It exists so that anyone — an
external contributor, a VillageSQL engineer, or an AI agent — can add a page
that reads like the rest of the site and holds up to review.

It covers **how to write** (voice, formatting, terminology, accuracy). For
**how to submit** (fork, branch, PR, issue-first policy), see
[CONTRIBUTING.md](./CONTRIBUTING.md). For the release/version mechanics, see
[VERSIONING.md](./VERSIONING.md).

If you only read one thing: **every claim in the docs must be true of the
running server.** VillageSQL is a MySQL-compatible database — a wrong example
doesn't just confuse, it breaks someone's production query. Accuracy is the
first rule, and everything else serves it.

---

## 1. Core principles

1. **Accuracy over everything.** Never document a feature, path, flag, or
   output you haven't verified. If you can't trace a claim to a merged change
   or a live server result, it doesn't ship. See [§10](#10-accuracy-and-verification).
2. **Upstream consistency.** If a feature behaves exactly like upstream MySQL,
   don't re-document it — link to the [MySQL documentation](https://dev.mysql.com/doc/).
   We write custom docs only for VillageSQL extensions, deviations, and additions.
3. **Single source of truth.** State each fact in one canonical place and link
   to it. Before removing something as "duplicate," cite the exact file and
   heading where the real copy lives. If you can't cite it, it stays.
4. **Just enough.** Document what a reader needs to succeed — no more, no less.
   Make content evergreen where you can.
5. **Serve both readers.** Human developers read to understand; AI agents read
   to execute. Write so both succeed. See [§9](#9-writing-for-humans-and-agents).

---

## 2. Choose the right page type

Before writing, decide what kind of page you're creating. Mixing a tutorial, a
reference table, and a design essay on one page is the most common way docs go
wrong. VillageSQL organizes content along the lines of the
[Diátaxis](https://diataxis.fr/) framework:

| Page type | Answers | Lives in | Shape |
|---|---|---|---|
| **Guide / how-to** | "How do I accomplish X?" | `guides/` | Task-focused steps for a competent user solving a real problem |
| **Tutorial** | "Teach me by doing" | `guides/`, quickstarts | Guided lesson that ends in a working result |
| **Reference** | "What are the exact facts?" | `mysql-8.4/<version>/` | Accurate, complete, dry — functions, types, syntax, options |
| **Explanation** | "Why does it work this way?" | `mysql-8.4/<version>/` (e.g. `architecture.mdx`) | Background, rationale, mental models |

Keep the modes separate. A reference page states facts; it doesn't teach. A
guide walks a path; it doesn't enumerate every option. If a page is trying to
do two jobs, split it.

---

## 3. Voice and tone

Write like a sharp, helpful human — clear, direct, and welcoming. Not stiff,
not chatty, not salesy.

- **Second person.** Address the reader as "you." ("You install the extension
  with…") Don't narrate as "we" or "the user" in reference and how-to content.
- **Present tense.** "The server returns a warning," not "will return."
- **Active voice.** Name who does the action. "VillageSQL parses the type
  parameters," not "the type parameters are parsed."
- **Condition before instruction.** "To list installed extensions, query
  `INFORMATION_SCHEMA.EXTENSIONS`." — the goal first, then the action.
- **Contractions are fine.** "don't," "can't," "you'll" read naturally.
- **Lead concrete, then abstract.** Show the example, then explain the mechanism.
- **Be specific.** Name the function, the error code, the exact output. Vague
  claims ("this improves performance") need a number or they get cut.
- **Say what you're unsure of, or verify it.** Never paper over a gap with
  confident-sounding filler. If you don't know, find out or leave it out.
- **Define terms on first use.** Don't assume the reader has read another page.

### Words and phrases to avoid

| Avoid | Why | Use instead |
|---|---|---|
| just, simply, easy, easily | Condescending; what's easy for you may not be for the reader | Omit, or state the actual steps |
| leverage, utilize, harness | Corporate filler | use |
| robust, seamless, powerful, game-changer, cutting-edge | Marketing adjectives that carry no information | State the concrete capability |
| It's important to note that…, It's worth noting… | Throat-clearing | Just state the point |
| in order to | Wordy | to |
| Furthermore, Moreover, Additionally | Mechanical transitions | A natural connector, or a new sentence |
| currently, at the moment, new, soon | Time-relative words that rot | State the version it applies to |
| "This isn't X, it's Y" / "Not X. Y." | Empty reframing tic | State the positive claim directly |

Match energy to the topic. Reference docs are calm and factual. A quickstart can
be a little warmer. Nothing needs hype.

---

## 4. Formatting

- **Headings in sentence case.** "Create a custom type," not "Create A Custom
  Type." Capitalize only the first word and proper nouns (SQL keywords, product
  names, type names like `TVECTOR`).
- **Don't use custom heading anchors.** The `## Heading {#my-id}` syntax breaks
  the Mintlify build (acorn parse error). Mintlify generates anchors from
  heading text automatically.
- **Lists:** numbered for sequences and ordered steps, bulleted for everything
  else. Keep items parallel in grammar.
- **Tables** for anything with two or more attributes per row (options, types,
  comparisons).
- **Admonitions** — use Mintlify's `<Note>`, `<Info>`, `<Warning>`, `<Tip>`,
  and `<CardGroup>`/`<Card>` components to set off asides and navigation. Don't
  overuse them; a page that is all callouts has none.
- **Em dashes:** avoid them. A comma, colon, period, or parentheses is almost
  always clearer.
- **Bold sparingly** — one or two genuinely key phrases per section, not as
  decoration.
- **No horizontal rules (`---`) inside body content.** Use headings and
  whitespace to separate sections. (The `---` fences around YAML frontmatter are
  required and are not affected by this.)
- **Numbers as digits** ("3 parameters," not "three parameters").

---

## 5. Code, CLI, and SQL

- **Always tag the language** on fenced code blocks (` ```sql `, ` ```bash `,
  ` ```json `, ` ```cpp `, ` ```rust `). Untagged blocks lose syntax
  highlighting.
- **Every example must run.** Test it against a real server before it ships
  ([§10](#10-accuracy-and-verification)). Never paste an example you haven't executed.
- **Copy-paste ready.** A reader should be able to copy a command and run it
  without editing anything that isn't a clearly marked placeholder.
- **Placeholders in `UPPER_SNAKE_CASE`.** Follow each with a lowercase
  description of what to substitute — e.g. replace `EXTENSION_NAME` with the
  name of the extension you're installing.
- **Show expected output** when it helps the reader confirm success. Trim
  irrelevant rows; use `...` to mark omitted output.
- **SQL conventions:**
  - Uppercase keywords (`SELECT`, `INSTALL EXTENSION`, `INFORMATION_SCHEMA`),
    lowercase identifiers.
  - Extension names in `INSTALL EXTENSION` are **identifiers, not strings**:
    `INSTALL EXTENSION vsql_uuid;` — the quoted form
    (`INSTALL EXTENSION 'vsql_uuid';`) is a syntax error. `VERSION 'x.y.z'` is
    a string literal and keeps its quotes.
  - When syntax is version-specific, say which version it applies to.
- **Don't apply MySQL UDF concepts to VEF.** `SONAME`, `mysql.func`, and
  `information_schema.routines` are UDF machinery and do **not** apply to
  VillageSQL extensions. Extensions install with `INSTALL EXTENSION` and appear
  in `INFORMATION_SCHEMA.EXTENSIONS`.
- **Don't document `villagesql.*` internal tables.** They are restricted from
  user connections (Error 3554).

---

## 6. Terminology

Use these terms exactly. Getting them wrong is a factual error, not a style nit.

| Term | Meaning | Notes |
|---|---|---|
| **VEF** | VillageSQL Extension Framework | The system for building extensions in C++ or Rust |
| **VEB** | VillageSQL Extension Bundle | The `.veb` package file. Names use underscores: `vsql_ai.veb` |
| **VDF** | VillageSQL Defined Function | A function registered through VEF — not a MySQL UDF |
| **Victionary** | VillageSQL's metadata/registry layer | — |
| **extension** | An installable VEF package | Install with `INSTALL EXTENSION name;` (unquoted identifier) |

**Product and identifier casing:** *VillageSQL* (one word, camel-cased S-Q-L),
*MySQL*, *InnoDB*. Type names as the server spells them: `TVECTOR(3)`,
`VECTOR(1536)`. SQL keywords uppercase.

**Framings to get right** (these have been corrected before — don't reintroduce
the wrong version):

- **Type parameters** (the `1536` in `VECTOR(1536)`): the engine parses and
  persists them and passes them to the extension, which interprets them. Do
  **not** call this "semantic type awareness" — the engine doesn't compute
  meaning from parameters on its own.
- **Column Storage ABI:** a **capability** feature — it lets extensions define a
  custom on-disk layout instead of routing through `VARBINARY`. Don't frame it
  as a performance optimization.
- **tvector:** a test/example vector type shipped as a *separate installable
  extension* (`INSTALL EXTENSION vsql_tvector`), not built into the server. The
  "t" means "test."
- **Verify status before claiming a feature ships.** "The framework exists" is
  not "the feature ships." Anything still in progress (for example, features not
  yet merged) must not be documented as available. See [§10](#10-accuracy-and-verification).

When in doubt about a definition, check the running server or ask — don't guess.

---

## 7. Frontmatter

Every `.mdx` file starts with YAML frontmatter. Missing frontmatter is a build
and review failure.

**All pages:**

```yaml
---
title: "Clear, descriptive page title"
description: "One sentence, ~140–160 characters, stating what the page is for."
---
```

**Guides** (`guides/`) may also set:

```yaml
sidebarTitle: "Short title"   # shown in the nav when the full title is long
keywords: "comma, separated, search terms"
```

**Versioned pages** under `mysql-8.4/<version>/` **must** declare an audience:

```yaml
audience: extension-author    # writing C++/Rust extensions with the SDK
# or
audience: server-contributor  # working on VillageSQL server internals
```

Set `audience` *before* you write the body — it forces the question "who is this
for?" up front. On **extension-author** pages, keep raw C ABI internals out of
the prose (raw typedefs like `vef_invalue_t`, raw result constants like
`VEF_RESULT_*`, `result->type` field access); those belong on the protocol
reference page only. A maintainer CI check (`freshness.py --check-docs`) enforces
the audience field and the raw-ABI rule.

---

## 8. Files, structure, and versioning

```
villagesql-docs/
├── docs.json              # navigation, theme, version dropdown — register new pages here
├── index.mdx              # docs landing page
├── guides/                # how-to guides and tutorials (see also: keywords, cross-links)
├── mysql-8.4/
│   ├── 0.0.4/             # current stable
│   ├── 0.0.5-dev/         # active development — most edits go here
│   └── 0.0.1 … 0.0.3/     # archived stable versions
├── extensions/
├── snippets/              # reusable MDX fragments
└── ja/ ko/ zh/            # translations
```

- **Edit the dev version.** New content and changes go to the current dev
  directory (`mysql-8.4/0.0.5-dev/`). Released versions are frozen except for
  corrections. The full release process is in [VERSIONING.md](./VERSIONING.md).
- **Register new pages in `docs.json`.** A file that isn't in `docs.json` won't
  appear in the sidebar.
- **Don't back-port syntax to a version that predates the feature.** Before
  changing an older version's page to reference a newer API, confirm that API
  existed when that version was released.
- **Stable and dev are not duplicate content.** They start identical and diverge
  as features land. Don't `noindex` current stable or dev — noindexing older
  archived versions is handled by the maintainer release workflow, not by
  contributors.
- **Breaking changes:** when a real breaking change lands, add a
  `breaking-changes.mdx` to that version and link to it from affected pages with
  a `<Warning>`. Don't pre-create it.

---

## 9. Writing for humans and agents

VillageSQL docs are read by people *and* by AI agents executing tasks. The two
fail differently: humans get confused by missing context; agents fail on
ambiguity and missing prerequisites.

Default structure that serves both: **action → detail → rationale.** The agent
gets the command first; the human gets the "why" at the end.

- **State prerequisites before the commands, never after.**
- **No ambiguous pronouns in procedural steps.** Name the file, the table, the
  variable — not "it" or "this."
- **Make success verifiable.** Say what the reader should see: the output, the
  exit code, the row that appears.
- **Commands are complete.** No undefined placeholders, no "…and so on."
- **For humans:** lead with why, establish the mental model before the steps,
  and include a recovery path ("if this fails, check…").

A quick test: could an agent with no prior context follow this page top to
bottom and succeed? Could a human skim it and understand *why*? If either
answer is no, revise.

---

## 10. Accuracy and verification

This is the rule that makes the docs trustworthy. Treat documented behavior as
an assertion that must match the product.

**Before you write, verify what exists:**

- Confirm files and paths (`ls`), code snippets (read the source), and CLI
  flags (`<command> --help`). Don't assert from memory when a lookup takes
  seconds.

**Before it's considered done, verify what it claims:**

- Run **every** statement, function call, and command in the page against a
  current VillageSQL server and confirm the real output matches what the page
  shows. If your local build is stale, rebuild first — never test docs against
  an out-of-date server.
- "Simulate the docs" means *write a test*, not render the markdown. The proof
  is a live server result.

**Never announce what hasn't shipped.** Every capability claim must trace to a
merged change or a passing test on the running server. In-progress work may be
described as "coming" but never as available.

**When you submit,** include a short verification table so reviewers can trust
the page:

```markdown
**Verified on:** `<server version>` (commit `<hash>`)

| Claim | Verified via | Result |
|---|---|---|
| Server is on this version | `SELECT VERSION()` | ✅ |
| <specific claim> | <source file:line, or "live query"> | ✅ |
```

One row per verifiable claim. Use `file:line` for code-backed claims and "live
query" for runtime-verified ones. This is the industry "docs-as-tests" practice
— it isn't a local quirk, and it's non-negotiable for anything that describes
server behavior.

---

## 11. Links, cross-linking, and accessibility

- **Internal links are relative** (`/guides/ai-prompts-in-mysql`), never
  absolute URLs. Absolute links to our own site break in preview and
  translation.
- **Descriptive link text.** Link the words that describe the destination
  ("see the [custom types reference](…)"), never "click here" or "read more."
  The link text should make sense read on its own.
- **Guides cross-link.** End a guide with a `## See also` section listing 2–4
  related guides, one line each on why they're relevant — and add the reciprocal
  link from those guides back. Related guides form topical clusters
  (performance, security, AI/embeddings, networking, and so on).
- **Alt text on every meaningful image**, describing what it shows in a sentence.
  Purely decorative images get empty alt text.

---

## 12. Before you submit

A quick checklist. Most of these map to a section above.

- [ ] Frontmatter present: `title`, `description` (and `audience` on versioned pages)
- [ ] Right page type, and it does one job (§2)
- [ ] Second person, present tense, active voice (§3)
- [ ] Sentence-case headings; no `{#custom-id}` anchors (§4)
- [ ] Code blocks tagged with a language; placeholders in `UPPER_SNAKE_CASE` (§5)
- [ ] Terminology correct; framings match §6
- [ ] **Every example run against a live server; output matches** (§10)
- [ ] No unshipped features presented as available (§10)
- [ ] Internal links relative; descriptive link text; alt text on images (§11)
- [ ] New pages registered in `docs.json` (§8)
- [ ] Edits went to the dev version unless correcting a released one (§8)
- [ ] Upstream-identical behavior links to MySQL docs instead of duplicating (§1)
- [ ] Verification table included in the PR (§10)

---

## Lineage

This guide adapts widely used documentation standards to VillageSQL:

- [Google Developer Documentation Style Guide](https://developers.google.com/style) — voice, sentence-case headings, code and placeholder conventions, accessibility
- [Diátaxis](https://diataxis.fr/) — the four documentation types (§2)
- [Docs as Tests](https://www.docsastests.com/) — verifying documented behavior against the product (§10)

For prose beyond the docs (blog posts, release notes, announcements), the
VillageSQL voice standard applies in addition to this guide.
