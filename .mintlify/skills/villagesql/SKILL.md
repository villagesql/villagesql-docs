---
name: villagesql
description: >
  Use when a user wants to set up VillageSQL Server, or to install, list, or
  uninstall VillageSQL extensions. VillageSQL is a drop-in replacement for
  MySQL with extensions, which add custom data types, custom functions, and
  custom indexes.
license: CC-BY-4.0
metadata:
  author: villagesql
---

# VillageSQL

VillageSQL is a drop-in replacement for MySQL with extensions. Extensions add
custom data types, custom functions, and custom indexes. You install each one
with one SQL statement, and the server does not need a restart.
VillageSQL Server is free and open source under the GNU General Public
License, version 2 (GPLv2).

## Set up a server

To install a server, fetch
[https://raw.githubusercontent.com/villagesql/villagesql-skills/main/skills/vsql-install-server/SKILL.md](https://raw.githubusercontent.com/villagesql/villagesql-skills/main/skills/vsql-install-server/SKILL.md)
and follow it. It installs a server, connects, and installs an extension to
prove that the server works.

To give later sessions the full set of VillageSQL skills, also run this
installer. It needs curl and git:

```bash
curl -sSL https://villagesql.com/skills | bash
```

## Use extensions

Each extension is a `.veb` file in the server's extension directory. To see
that directory, run `SHOW VARIABLES LIKE 'veb_dir';`. The install script and
the Docker image put the VillageSQL extensions there for you.

```sql
-- Install an extension. The name is an identifier: do not quote it.
INSTALL EXTENSION vsql_uuid;

-- List the installed extensions and their versions.
SELECT EXTENSION_NAME, EXTENSION_VERSION FROM INFORMATION_SCHEMA.EXTENSIONS;

-- Call its functions, and use its custom type in a column.
SELECT uuid_v4();
CREATE TABLE orders (id vsql_uuid.UUID PRIMARY KEY);
INSERT INTO orders VALUES (uuid_v7());

-- Uninstall it. This fails while a column still uses its custom type.
UNINSTALL EXTENSION vsql_uuid;
```

Two errors are common:

- `INSTALL EXTENSION 'vsql_uuid';` fails with `ERROR 1064 (42000)`, because
  the name is quoted. Write it without quotes.
- `UNINSTALL EXTENSION` fails with `ERROR 3219 (HY000): Cannot drop extension
  ... as 1 column(s) depend on it` while a column uses the extension's custom
  type. Drop the column, or its table, first.

## Find more

- The extension catalog has one page for each extension:
  [https://villagesql.com/docs/en/extensions/catalog.md](https://villagesql.com/docs/en/extensions/catalog.md)
- To build your own extension in C++ or Rust, read
  [https://villagesql.com/docs/en/extensions/build/create.md](https://villagesql.com/docs/en/extensions/build/create.md)
- The docs list every page for agents at [https://villagesql.com/docs/llms.txt](https://villagesql.com/docs/llms.txt).
- Read any docs page as Markdown by adding `.md` to its address.
- The docs are also in Japanese, Korean, Chinese, and Brazilian Portuguese.
  Replace `/en/` in an address with `/ja/`, `/ko/`, `/zh/`, or `/pt-BR/`. The
  guides, the tutorial, and the dev-release pages are in English only.
