# Backend Pro Max — JetBrains Plugin

Stub plugin for IntelliJ IDEA / GoLand / PyCharm / WebStorm.

## Features

- **Tools → Backend Pro Max → Search Knowledge Base** — input dialog → `backendpro --json` → results dialog
- **Tools → Backend Pro Max → Explain Selection** — selected text → search → results dialog

## Requirements

- `backendpro` CLI installed and on PATH (`pip install backendpro`)

## Building

This is a stub. To build a full plugin, use the IntelliJ Platform Gradle Plugin:

```bash
# In a Gradle project with intellij-platform-plugin
./gradlew buildPlugin
```

## Status

MVP stub — shells out to CLI. Future versions can use MCP transport.
