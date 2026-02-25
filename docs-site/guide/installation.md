# Installation

## System Requirements

- **Python 3.12** or later
- **Graphviz** — required for diagram rendering

Install Graphviz for your platform:

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

## Install with pip

```sh
pip install microsoft.azure-diagram-mcp-server
```

## Install with uv

[uv](https://docs.astral.sh/uv/) is the recommended Python package manager for fast, reliable installs:

```sh
uv pip install microsoft.azure-diagram-mcp-server
```

Or run directly without installing:

```sh
uvx microsoft.azure-diagram-mcp-server
```

## Docker

Pull the pre-built image:

```sh
docker pull ghcr.io/microsoft/diagrams-mcp-server
```

Or build from source:

```sh
git clone https://github.com/microsoft/diagrams-mcp-server.git
cd diagrams-mcp-server
docker build -t microsoft/azure-diagram-mcp-server .
```

Configure your MCP client to use Docker:

```json
{
  "mcpServers": {
    "azure-diagram": {
      "command": "docker",
      "args": [
        "run", "--rm", "--interactive",
        "--env", "FASTMCP_LOG_LEVEL=ERROR",
        "microsoft/azure-diagram-mcp-server:latest"
      ]
    }
  }
}
```

## From Source

Clone and install in development mode:

```sh
git clone https://github.com/microsoft/diagrams-mcp-server.git
cd diagrams-mcp-server
pip install -e ".[dev]"
```

Or with uv:

```sh
git clone https://github.com/microsoft/diagrams-mcp-server.git
cd diagrams-mcp-server
uv pip install -e ".[dev]"
```

## Verify Installation

Run the server directly to verify it starts correctly:

```sh
microsoft.azure-diagram-mcp-server
```

The server will start and listen for MCP connections over stdio.
