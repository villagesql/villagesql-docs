# VillageSQL Server Documentation

This repository contains the official documentation for VillageSQL Server for MySQL - a community-driven, extensible fork of MySQL that is a drop-in replacement.

## About VillageSQL

VillageSQL is the innovation platform for MySQL and a new path for MySQL in the agentic AI era. VillageSQL Server for MySQL is an open-source, drop-in replacement, and extensible tracking fork of MySQL. It introduces a robust extension framework that supports custom data types and custom functions (with custom indexes coming soon). VillageSQL's mission is to empower the MySQL community by enabling permissionless innovation. We have built a few extensions to showcase the framework, including:

- Network Address data types
- UUID
- Cryptographic functions
- SQL-based LLM prompting

## Documentation Site

View the documentation at [docs.villagesql.com](https://villagesql.com/docs)

## Development

We welcome suggestions. The documentation pages are built using Mintlify. Install the [Mintlify CLI](https://www.npmjs.com/package/mint) to preview your documentation changes locally. To install, use the following command:

```
npm i -g mint
```

Run the following command at the root of your documentation, where your `docs.json` is located:

```
mint dev
```

View your local preview at `http://localhost:3000`.

## Publishing changes

Install the Mintlify GitHub app from your [dashboard](https://dashboard.mintlify.com/settings/organization/github-app) to propagate changes from your repo to the live site. Changes are deployed to production automatically after pushing to the default branch.

## Contributing

We welcome contributions to improve our documentation! Please see our [contributing guidelines](./CONTRIBUTING.md) for more information.

## Community

- [GitHub Issues](https://github.com/villagesql/villagesql-server/issues) - Report bugs or request new features
- [Discussions](https://github.com/villagesql/villagesql-server/discussions) - Join the discussion on GitHub Discussions
- [Discord](https://discord.gg/KSr6whd3Fr) - Chat with the community on Discord

## Troubleshooting

- If your dev environment isn't running: Run `mint update` to ensure you have the most recent version of the CLI.
- If a page loads as a 404: Make sure you are running in a folder with a valid `docs.json`.

## Resources

- [VillageSQL Server GitHub](https://github.com/villagesql/villagesql-server)
- [Mintlify documentation](https://mintlify.com/docs)
