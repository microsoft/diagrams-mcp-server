# Getting Started

Azure Diagram MCP Server is a [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that generates professional diagrams using the Python [diagrams](https://diagrams.mingrammer.com/) package DSL — with first-class support for Azure architecture diagrams.

Generate Azure architecture diagrams, sequence diagrams, flow charts, class diagrams, Kubernetes diagrams, and more — all from natural language via your AI assistant.

## Prerequisites

- **Python 3.12+** — Install via [python.org](https://www.python.org/downloads/) or `uv python install 3.12`
- **Graphviz** — Install from [graphviz.org](https://www.graphviz.org/) or via your package manager:

::: code-group
```sh [macOS]
brew install graphviz
```
```sh [Ubuntu/Debian]
sudo apt-get install graphviz
```
```sh [Windows]
choco install graphviz
```
:::

- **uv** (recommended) — Install from [Astral](https://docs.astral.sh/uv/getting-started/installation/)

## Quick Install

The fastest way to get started is with `uvx`, which requires no separate install step:

```sh
uvx microsoft.azure-diagram-mcp-server
```

Or install with pip:

```sh
pip install microsoft.azure-diagram-mcp-server
```

## Configure Your MCP Client

### VS Code

Add to your VS Code `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "azure-diagram": {
        "command": "uvx",
        "args": ["microsoft.azure-diagram-mcp-server"]
      }
    }
  }
}
```

### Copilot CLI

```sh
copilot mcp add azure-diagram -- uvx microsoft.azure-diagram-mcp-server
```

## Your First Diagram

Once configured, ask your AI assistant to generate a diagram. For example:

> "Create an Azure architecture diagram with an Application Gateway routing traffic to an App Service and Azure Functions, both connecting to a Cosmos DB database."

The server will generate and execute the Python code to produce a professional diagram image.

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `generate_diagram` | Generate a diagram from Python code using the diagrams DSL |
| `get_diagram_examples` | Get example code for different diagram types |
| `list_icons` | Discover available icons by provider and service |

## Next Steps

- [Installation](/guide/installation) — Explore all installation methods including Docker
- [Examples](/guide/examples) — See example diagrams and code
