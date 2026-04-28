# Backend Pro Max — VS Code Extension

Search 30+ backend & distributed-systems knowledge domains directly from your editor.

## Features

- **Search** — `Cmd+Shift+P` → "Backend Pro Max: Search" to query the knowledge base
- **Explain Selection** — Right-click selected text → "Backend Pro Max: Explain Selection"
- **CodeLens** — Stack-specific guidelines shown inline at the top of supported files (Go, Python, Java, TypeScript, Rust, etc.)
- **MCP Mode** — Optionally connect to the `backendpro-mcp` server for richer results

## Requirements

- [Backend Pro Max CLI](https://github.com/shashankswe2020-ux/backend-pro-max-skill) installed (`pip install backendpro`)
- Python 3.8+

## Extension Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `backendpro.path` | `backendpro` | Path to the CLI executable |
| `backendpro.defaultDomain` | (empty) | Default domain filter |
| `backendpro.useMcp` | `false` | Use MCP server instead of CLI |
| `backendpro.mcpCommand` | `backendpro-mcp` | MCP server command |
| `backendpro.codeLens.enabled` | `true` | Show CodeLens guidelines |
| `backendpro.codeLens.maxResults` | `3` | Max CodeLens entries |

## Development

```bash
cd extensions/vscode
npm install
npm run compile
npm test
npx @vscode/vsce package  # produces .vsix
```
