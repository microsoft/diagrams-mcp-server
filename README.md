# Azure Diagram MCP Server

[![Tests](https://img.shields.io/badge/tests-140_passing-brightgreen.svg)](https://github.com/microsoft/diagrams-mcp-server/actions)
[![PyPI](https://img.shields.io/pypi/v/microsoft.azure-diagram-mcp-server.svg)](https://pypi.org/project/microsoft.azure-diagram-mcp-server/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-server-purple.svg)](https://modelcontextprotocol.io/)
[![Copilot SDK](https://img.shields.io/badge/Copilot_SDK-integrated-blue.svg)](https://github.com/github/copilot-sdk)

An [MCP](https://modelcontextprotocol.io/) server for generating professional infrastructure diagrams using the Python [diagrams](https://diagrams.mingrammer.com/) DSL — with first-class Azure support and [GitHub Copilot SDK](https://github.com/github/copilot-sdk) integration for natural language diagram generation.

```mermaid
graph LR
    A[AI Assistant] -->|Natural Language| B[MCP Server]
    B -->|Python DSL| C[Diagrams + Graphviz]
    C -->|PNG| D[MCP Apps Viewer]
    B -->|Security Scan| E[AST + Bandit]
    E -->|Pass| C
```

## Getting Started

### Step 1 — Install Prerequisites

| Dependency | Install | Verify |
|-----------|---------|--------|
| **uv** | [astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) | `uv --version` |
| **Python 3.12+** | `uv python install 3.12` | `python3 --version` |
| **Graphviz** | `brew install graphviz` / `apt install graphviz` / [graphviz.org](https://www.graphviz.org/) | `dot -V` |

> **⚠️ Graphviz is required.** Without it the MCP server will fail to start. Verify with `dot -V` before proceeding.

### Step 2 — Verify the Server Starts

Run the server directly to confirm everything works:

```bash
uvx microsoft.azure-diagram-mcp-server
```

You should see a message confirming the server is installed and ready. The server is an MCP stdio server — it's designed to be launched by an MCP client, not run directly. If it fails to install, check that Graphviz is installed (`dot -V`).

### Step 3 — Connect to Your AI Host

Pick **one** of the methods below to register the server with your AI host.

#### Copilot CLI

1. Start a Copilot CLI session:

   ```bash
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

> The config is saved to `~/.copilot/mcp-config.json`. You can also edit that file directly:
>
> ```json
> {
>   "servers": {
>     "azure-diagram": {
>       "type": "local",
>       "command": "uvx microsoft.azure-diagram-mcp-server",
>       "tools": ["*"]
>     }
>   }
> }
> ```

#### VS Code (one-click)

[![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-007ACC?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Azure%20Diagram%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22microsoft.azure-diagram-mcp-server%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D)

Or add manually to your VS Code `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "azure-diagram": {
        "command": "uvx",
        "args": ["microsoft.azure-diagram-mcp-server"],
        "env": {
          "FASTMCP_LOG_LEVEL": "ERROR"
        }
      }
    }
  }
}
```

#### Docker

```bash
docker build -t microsoft/azure-diagram-mcp-server .
```

```json
{
  "mcp": {
    "servers": {
      "azure-diagram": {
        "command": "docker",
        "args": ["run", "--rm", "-i", "--env", "FASTMCP_LOG_LEVEL=ERROR",
                 "microsoft/azure-diagram-mcp-server:latest"]
      }
    }
  }
}
```

## Features

| Feature | Description |
|---------|-------------|
| ☁️ **Azure-First** | 100+ Azure service icons — App Service, Functions, Cosmos DB, AKS, and more |
| 🌐 **Multi-Cloud** | AWS, GCP, Kubernetes, on-premises, and custom icon support |
| 📊 **Multiple Types** | Architecture, sequence, flow, class, K8s, and custom diagrams |
| 🔒 **Security Scanning** | AST + Bandit code analysis before every execution |
| 🖼️ **MCP Apps Viewer** | Interactive diagram viewer with pan, zoom, download, and dark/light theme |
| 🤖 **Copilot SDK** | Natural language diagram generation via GitHub Copilot SDK |

## Architecture

```mermaid
graph TB
    subgraph "GitHub Copilot"
        CLI[Copilot CLI]
        VS[VS Code Copilot]
    end

    subgraph "MCP Server"
        S[server.py<br/>FastMCP]
        DT[diagram_tools.py<br/>Generation + Examples]
        SC[scanner.py<br/>AST + Bandit]
        V[viewer/app.html<br/>MCP Apps Viewer]
    end

    subgraph "Copilot SDK Layer"
        CC[copilot_client.py<br/>DiagramCopilotClient]
        AG[Custom Agent<br/>azure-diagram-architect]
    end

    CLI & VS -->|MCP stdio| S
    CC -->|MCP local| S
    AG --> CC
    S --> DT
    S --> V
    DT --> SC
    SC -->|Pass| DT
    DT -->|Python DSL| GV[Graphviz → PNG]
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `generate_diagram` | Execute Python diagram code with security scanning and timeout. Pre-imports all providers — just start with `with Diagram(...)`. |
| `refresh_diagram` | Regenerate a diagram from updated code (app-only, used by the MCP Apps viewer). |
| `get_diagram_examples` | Get example code by type: `azure`, `sequence`, `flow`, `class`, `k8s`, `onprem`, `custom`, or `all`. |
| `list_icons` | Discover available icons by provider and service. Filter with `provider_filter` and `service_filter`. |

### Recommended Workflow

```mermaid
sequenceDiagram
    participant User
    participant Copilot as GitHub Copilot
    participant MCP as MCP Server
    participant App as MCP Apps Viewer

    User->>Copilot: "Create an Azure web app diagram"
    Copilot->>MCP: list_icons(provider_filter="azure")
    MCP-->>Copilot: Available icons
    Copilot->>MCP: get_diagram_examples(diagram_type="azure")
    MCP-->>Copilot: Example code
    Copilot->>MCP: generate_diagram(code="...")
    MCP-->>Copilot: PNG + structuredContent
    Copilot->>App: Render diagram in viewer
    App-->>User: Interactive diagram with pan/zoom
```

## MCP Apps Viewer

The server includes an interactive **MCP Apps** viewer that renders diagrams inline in VS Code and the Copilot CLI. When `generate_diagram` returns a result, the viewer is automatically displayed.

```mermaid
graph LR
    subgraph "MCP Server"
        GD[generate_diagram] -->|CallToolResult| SC[structuredContent<br/>status + imageData]
        SC --> META["_meta.ui.resourceUri<br/>ui://diagram-viewer/app.html"]
    end

    subgraph "MCP Apps Viewer"
        META --> V[Interactive Viewer]
        V --> PAN[Pan & Drag]
        V --> ZOOM[Zoom In/Out]
        V --> DL[Download PNG]
        V --> THEME[Dark/Light Theme]
        V --> FIT[Fit to View]
    end
```

| Feature | Control |
|---------|---------|
| **Pan** | Click and drag |
| **Zoom** | Mouse wheel, `+` / `-` keys |
| **Fit to view** | `0` key or toolbar button |
| **Download** | Toolbar download button |
| **Theme** | Toggle dark/light in toolbar |

The viewer is served as an MCP resource at `ui://diagram-viewer/app.html` and receives the diagram as base64-encoded PNG via `structuredContent.imageData`.

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

## Copilot SDK Integration

The server includes a [GitHub Copilot SDK](https://github.com/github/copilot-sdk) client that provides a natural language interface to diagram generation — describe what you want and the Copilot-powered architect generates it.

```mermaid
graph LR
    U[User Prompt] --> CC[DiagramCopilotClient]
    CC -->|Creates Session| CS[CopilotClient]
    CS -->|Connects| MCP[Diagram MCP Server]
    CS -->|Uses| AG[azure-diagram-architect<br/>Custom Agent]
    MCP -->|Returns| IMG[PNG Diagram]
```

### Interactive CLI

```bash
uv run microsoft.azure-diagram-copilot
```

### Programmatic Usage

```python
import asyncio
from microsoft.azure_diagram_mcp_server.copilot_client import DiagramCopilotClient

async def main():
    async with DiagramCopilotClient(model="gpt-4.1") as client:
        client.on_delta(lambda delta: print(delta, end="", flush=True))
        client.on_idle(lambda: print())

        await client.generate(
            "Create a 3-tier Azure architecture with App Gateway, "
            "App Service, and Cosmos DB"
        )

asyncio.run(main())
```

### BYOK (Bring Your Own Key)

Use your own LLM provider — no Copilot subscription required:

| Variable | Description |
|----------|-------------|
| `DIAGRAM_COPILOT_PROVIDER_TYPE` | `openai`, `azure`, or `anthropic` |
| `DIAGRAM_COPILOT_BASE_URL` | API endpoint URL |
| `DIAGRAM_COPILOT_API_KEY` | API key |
| `DIAGRAM_COPILOT_WIRE_API` | `completions` or `responses` |
| `DIAGRAM_COPILOT_MODEL` | Model override (default: `gpt-4.1`) |
| `DIAGRAM_COPILOT_AZURE_API_VERSION` | Azure API version (default: `2024-10-21`) |

```bash
export DIAGRAM_COPILOT_PROVIDER_TYPE=azure
export DIAGRAM_COPILOT_BASE_URL=https://your-resource.openai.azure.com
export DIAGRAM_COPILOT_API_KEY=your-api-key
uv run microsoft.azure-diagram-copilot
```

### Resumable Sessions

```python
client = DiagramCopilotClient(session_id="my-project-diagrams")
await client.start()
await client.generate("Create an Azure web app diagram")

# Resume later
await client.resume("my-project-diagrams")
await client.generate("Add a Redis cache to the previous diagram")
await client.stop()
```

## Development

```bash
# Setup
uv sync --group dev

# Test (140 tests, 9 skip without Graphviz)
uv run pytest tests/ -v

# Lint + format
uv run ruff check microsoft/ tests/
uv run ruff format --check microsoft/ tests/

# Type check
uv run pyright

# Coverage
uv run pytest --cov=microsoft --cov-report=term-missing tests/
```

See [AGENTS.md](AGENTS.md) for comprehensive contributor documentation covering architecture, conventions, testing patterns, CI/CD, and the GitHub Pages docs site.

## Documentation

📖 **[microsoft.github.io/diagrams-mcp-server](https://microsoft.github.io/diagrams-mcp-server/)** — Full documentation built with VitePress, deployed via GitHub Pages.

```bash
cd docs-site && npm install && npm run docs:dev  # Local dev server
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Contributing

This project welcomes contributions and suggestions. See [AGENTS.md](AGENTS.md) for the full development guide.