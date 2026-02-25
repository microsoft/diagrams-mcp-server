# Getting Started

Azure Diagram MCP Server is a [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that generates professional diagrams using the Python [diagrams](https://diagrams.mingrammer.com/) package DSL — with first-class support for Azure architecture diagrams.

Generate Azure architecture diagrams, sequence diagrams, flow charts, class diagrams, Kubernetes diagrams, and more — all from natural language via your AI assistant.

## Step 1 — Install Prerequisites

- **Python 3.12+** — Install via [python.org](https://www.python.org/downloads/) or `uv python install 3.12`
- **uv** (recommended) — Install from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
- **Graphviz** (**required**) — Install from [graphviz.org](https://www.graphviz.org/) or via your package manager:

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

::: warning Graphviz is required
Without Graphviz installed, the MCP server will fail to start. Verify it's installed by running `dot -V`.
:::

## Step 2 — Verify the Server Starts

Run the server directly to confirm your environment is set up correctly:

```sh
uvx microsoft.azure-diagram-mcp-server
```

You should see the server start and wait for MCP connections. Press **Ctrl+C** to stop it. If it crashes, check that Graphviz is installed (`dot -V`).

## Step 3 — Connect to Your AI Host

Pick **one** of the methods below to register the server with your AI host.

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

1. Start a Copilot CLI session:

   ```sh
   copilot
   ```

2. Inside the session, run the slash command:

   ```
   /mcp add
   ```

3. Fill in the form (use **Tab** to move between fields):

   | Field | Value |
   |-------|-------|
   | **Name** | `azure-diagram` |
   | **Type** | `Local` |
   | **Command** | `uvx microsoft.azure-diagram-mcp-server` |

4. Press **Ctrl+S** to save.

5. Verify with `/mcp show azure-diagram` — status should show **✓ Connected**.

::: tip Manual config
The config is saved to `~/.copilot/mcp-config.json`. You can also edit that file directly:

```json
{
  "servers": {
    "azure-diagram": {
      "type": "local",
      "command": "uvx microsoft.azure-diagram-mcp-server",
      "tools": ["*"]
    }
  }
}
```
:::

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
