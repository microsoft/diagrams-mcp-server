# Azure Diagram MCP Server

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/microsoft/diagrams-mcp-server/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

Model Context Protocol (MCP) server for generating professional diagrams using the Python [diagrams](https://diagrams.mingrammer.com/) package DSL — with first-class support for Azure architecture diagrams.

Generate Azure architecture diagrams, sequence diagrams, flow charts, class diagrams, Kubernetes diagrams, and more — all from natural language via your AI assistant.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
2. Install Python using `uv python install 3.12`
3. Install [GraphViz](https://www.graphviz.org/)

## Installation

| VS Code | Cursor |
|:-------:|:------:|
| [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-007ACC?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Azure%20Diagram%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22microsoft.azure-diagram-mcp-server%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=microsoft.azure-diagram-mcp-server&config=eyJjb21tYW5kIjoidXZ4IG1pY3Jvc29mdC5henVyZS1kaWFncmFtLW1jcC1zZXJ2ZXIiLCJlbnYiOnsiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9fQ==) |

### Manual Configuration

Add to your MCP client configuration (e.g., VS Code `settings.json`, Claude Desktop config):

```json
{
  "mcpServers": {
    "microsoft.azure-diagram-mcp-server": {
      "command": "uvx",
      "args": ["microsoft.azure-diagram-mcp-server"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Docker

After building with `docker build -t microsoft/azure-diagram-mcp-server .`:

```json
{
  "mcpServers": {
    "microsoft.azure-diagram-mcp-server": {
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

## Features

| Feature | Description |
|---------|-------------|
| **Azure Architecture Diagrams** | Full support for Azure services — App Service, Functions, Cosmos DB, AKS, and 100+ more |
| **Multi-Cloud Support** | Also supports AWS, GCP, Kubernetes, and on-premises diagrams |
| **Multiple Diagram Types** | Architecture, sequence, flow, class, and custom diagrams |
| **Security Scanning** | AST + Bandit-powered code scanning before execution |
| **Interactive Viewer** | MCP App integration for interactive diagram viewing with pan, zoom, and download |

## Quick Example

```python
from diagrams import Diagram
from diagrams.azure.compute import AppServices, FunctionApps
from diagrams.azure.database import CosmosDb
from diagrams.azure.network import ApplicationGateway

with Diagram("Azure Web Architecture", show=False):
    gateway = ApplicationGateway("Gateway")
    app = AppServices("App Service")
    functions = FunctionApps("Functions")
    db = CosmosDb("Cosmos DB")

    gateway >> app >> db
    gateway >> functions >> db
```

## MCP Tools

### `generate_diagram`
Generate a diagram from Python code using the diagrams package DSL. The runtime pre-imports all diagram providers — just start with `with Diagram(...)`.

### `get_diagram_examples`
Get example code for different diagram types: `azure`, `sequence`, `flow`, `class`, `k8s`, `onprem`, `custom`, or `all`.

### `list_icons`
Discover available icons organized by provider and service. Call without filters to see providers, then drill down.

## Development

### Setup
```bash
uv pip install -e ".[dev]"
```

### Testing
```bash
pytest -xvs tests/
```

### With Coverage
```bash
pytest --cov=microsoft.azure_diagram_mcp_server --cov-report=term-missing tests/
```

### Linting
```bash
ruff check .
ruff format --check .
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Contributing

This project welcomes contributions and suggestions. Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.