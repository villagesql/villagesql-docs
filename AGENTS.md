# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Mintlify documentation

## Development Commands

- `mint dev` - Start local development server at http://localhost:3000
- `mint update` - Update Mintlify CLI to latest version (run if dev environment isn't working)

## Architecture

This is a Mintlify documentation site with the following structure:

- **Configuration**: `docs.json` defines navigation (tabs, groups, pages), theme (almond), colors, logo, and contextual AI tool options
- **Content organization**:
  - `essentials/` - Core documentation content (markdown, code, images, settings, navigation)
  - `ai-tools/` - AI tool integration guides (cursor, claude-code, windsurf)
  - `api-reference/` - API documentation with OpenAPI spec
  - `snippets/` - Reusable content snippets
- **Navigation structure**: Two-tab layout (Guides, API reference) with nested groups
- **Deployment**: Auto-deploys to production via GitHub app integration when pushing to main branch

## Working relationship
- You can push back on ideas-this can lead to better documentation. Cite sources and explain your reasoning when you do so
- ALWAYS ask for clarification rather than making assumptions
- NEVER lie, guess, or make up anything

## Project context
- Format: MDX files with YAML frontmatter
- Config: docs.json for navigation, theme, settings
- Components: Mintlify components

## VillageSQL-Specific Information

### Server Binary and Commands
- **Server binary**: VillageSQL uses the standard MySQL server binary `mysqld` (NOT `villagesql-server`)
- **Starting the server**: Use `mysqld` or `mysqld_safe &` for production with auto-restart
- **Client connection**: Use standard MySQL client: `mysql -u root -p`
- **Default port**: 3306 (standard MySQL port)

### Extension System
VillageSQL's key differentiator is its extension framework. When documenting extensions:

- **Installation syntax**: `INSTALL EXTENSION 'extension_name';`
- **Verification**: `SHOW EXTENSIONS;` lists all installed extensions
- **Built-in extensions**: When building from source, `vsql_complex` and `vsql_simple` are included. Other extensions are available in separate GitHub repositories.
- **Example extensions**:
  - `vsql_complex`: Complex number data types (included in source builds)
  - `vsql_simple`: Minimal demonstration extension (included in source builds)
  - `vsql_uuid`: UUID generation and validation ([repo](https://github.com/villagesql/vsql-uuid))
  - `vsql_crypto`: Cryptographic functions ([repo](https://github.com/villagesql/vsql-crypto))
  - `vsql_network_address`: IPv4, IPv6, and MAC address types ([repo](https://github.com/villagesql/vsql-network-address))
  - `vsql_ai`: AI prompting via SQL ([repo](https://github.com/villagesql/vsql-ai))

### Installation Methods
1. Build from source: Follow instructions at villagesql.com/build

### Key URLs
- Installation: https://villagesql.com/install
- Documentation: https://villagesql.com/docs
- GitHub: https://github.com/villagesql/villagesql-server
- Discord: https://discord.gg/KSr6whd3Fr

## Content strategy
- Document just enough for user success - not too much, not too little
- Prioritize accuracy and usability
- Make content evergreen when possible
- Search for existing content before adding anything new. Avoid duplication unless it is done for a strategic reason
- Check existing patterns for consistency
- Start by making the smallest reasonable changes

## docs.json

- Refer to the [docs.json schema](https://mintlify.com/docs.json) when building the docs.json file and site navigation

## Frontmatter requirements for pages
- title: Clear, descriptive page title
- description: Concise summary for SEO/navigation

## Writing standards
- Second-person voice ("you")
- Prerequisites at start of procedural content
- Test all code examples before publishing
- Match style and formatting of existing pages
- Include both basic and advanced use cases
- Language tags on all code blocks
- Alt text on all images
- Relative paths for internal links

## Git workflow
- NEVER use --no-verify when committing
- Ask how to handle uncommitted changes before starting
- Create a new branch when no clear branch exists for changes
- Commit frequently throughout development
- NEVER skip or disable pre-commit hooks

## Do not
- Skip frontmatter on any MDX file
- Use absolute URLs for internal links
- Include untested code examples
- Make assumptions - always ask for clarification
