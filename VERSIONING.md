# Documentation Versioning Policy

## Workflow

**All changes go to the dev branch** (e.g., `mysql-8.4/0.0.3-dev/`)

### Cutting a Release

When releasing a new version:

1. **Rename dev to version number**
   ```bash
   mv mysql-8.4/0.0.3-dev mysql-8.4/0.0.3
   ```

2. **Update docs.json**
   - Rename version: `Development (0.0.3-dev)` → `Stable-alpha (0.0.3)`
   - Add `"default": true` to new stable (0.0.3)
   - Remove `"default": true` from old stable (0.0.2)

3. **Create new dev branch**
   ```bash
   cp -r mysql-8.4/0.0.3 mysql-8.4/0.0.4-dev
   ```
   - Add `Development (0.0.4-dev)` entry to docs.json

4. **All future changes go to new dev branch** (`mysql-8.4/0.0.4-dev/`)

## Archive Policy

- Keep **10 versions** in dropdown
- When adding version 11, remove oldest from `docs.json` (but keep files)
- Archived versions remain accessible via direct URL

---

Each version is ~132KB. Archived versions stay accessible at direct URLs like `villagesql.com/docs/mysql-8.4/0.0.1/quickstart`.
