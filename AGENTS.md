# AGENTS.md — Azure Diagram MCP Server

> Comprehensive onboarding guide for AI agents and human contributors working on this repository.

## Project Overview

**Azure Diagram MCP Server** is a Python [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that generates professional infrastructure and architecture diagrams using the [diagrams](https://diagrams.mingrammer.com/) package DSL. It has first-class Azure support and integrates with the [GitHub Copilot SDK](https://github.com/github/copilot-sdk) for natural language diagram generation.

**Key capability:** A user describes a diagram via the GitHub Copilot CLI or VS Code Copilot → the MCP server generates Python diagram code → executes it → returns a PNG image rendered in the MCP Apps viewer.

---

## Repository Structure

```
diagrams-mcp-server/
├── microsoft/                         # Main source package
│   └── azure_diagram_mcp_server/
│       ├── __init__.py                # Package init, version string
│       ├── server.py                  # FastMCP server — tool registration + entry point
│       ├── diagram_tools.py           # Core logic — diagram generation, examples, icon listing
│       ├── models.py                  # Pydantic models — request/response schemas, DiagramType enum
│       ├── scanner.py                 # Security scanner — AST analysis + Bandit integration
│       ├── copilot_client.py          # Copilot SDK client — natural language diagram interface
│       └── viewer/
│           └── app.html               # MCP Apps interactive diagram viewer (HTML/CSS/JS)
├── tests/
│   ├── conftest.py                    # Pytest fixtures — temp dirs, example code, dangerous code
│   ├── test_server.py                 # Server tool function tests (15 tests)
│   ├── test_diagram_tools.py          # Diagram generation + example tests (28 tests)
│   ├── test_models.py                 # Pydantic model validation tests (12 tests)
│   ├── test_scanner.py                # Security scanner tests (58 tests)
│   ├── test_copilot_client.py         # Copilot SDK client tests (37 tests)
│   └── resources/example_diagrams/    # Runnable example diagram scripts
├── docs-site/                         # VitePress documentation site
│   ├── .vitepress/config.ts           # Site config — nav, sidebar, theme
│   ├── index.md                       # Home page with hero + features
│   ├── guide/
│   │   ├── getting-started.md         # Quick start
│   │   ├── installation.md            # Install methods (uv, pip, Docker)
│   │   └── examples.md               # Diagram examples with code
│   └── public/                        # Static assets (logos, favicons)
├── .github/workflows/
│   ├── ci.yml                         # CI — Ruff lint, Pyright types, Pytest (Python 3.12+3.13)
│   └── docs.yml                       # Docs — VitePress build + GitHub Pages deploy
├── .pre-commit-config.yaml            # Pre-commit hooks (Ruff, Pyright, pytest on push)
├── Dockerfile                         # Multi-stage Docker build with Graphviz
├── pyproject.toml                     # Project metadata, dependencies, tool config
└── uv.lock                           # Dependency lockfile (uv package manager)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  GitHub Copilot (Copilot CLI, VS Code Copilot)          │
│  ← Natural language: "Create a 3-tier Azure diagram" →  │
└─────────────┬───────────────────────────────┬───────────┘
              │ MCP Protocol (stdio)          │ Copilot SDK
              ▼                               ▼
┌─────────────────────────┐   ┌───────────────────────────┐
│  FastMCP Server          │   │  DiagramCopilotClient     │
│  (server.py)             │   │  (copilot_client.py)      │
│                          │   │                           │
│  Tools:                  │   │  - CopilotClient session  │
│  • generate_diagram      │◄──│  - MCP server connection  │
│  • refresh_diagram       │   │  - Custom agent prompt    │
│  • get_diagram_examples  │   │  - Streaming + BYOK       │
│  • list_icons            │   └───────────────────────────┘
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  diagram_tools.py        │
│  • Code preprocessing    │
│  • Execution namespace   │
│  • Timeout handling      │
│  • Example definitions   │
│  • Icon discovery        │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│  scanner.py              │   │  Python diagrams DSL    │
│  • AST validation        │   │  + Graphviz renderer    │
│  • Bandit security scan  │   │  → PNG output           │
│  • Dangerous fn detect   │   └─────────────────────────┘
└─────────────────────────┘
```

### Data Flow

1. **Input:** User provides natural language or Python diagram code.
2. **Security scan:** `scanner.py` validates code with AST analysis + Bandit. Rejects imports, `exec()`, `eval()`, subprocess calls, dunder access, etc.
3. **Preprocessing:** `diagram_tools.py` injects `show=False`, sets the output filename, and builds an execution namespace with all diagram provider modules pre-imported.
4. **Execution:** Code runs in the prepared namespace with a platform-aware timeout (SIGALRM on Unix, threading on Windows).
5. **Output:** Generated PNG is returned as base64-encoded data in the MCP `CallToolResult` with `structuredContent` for the MCP Apps viewer.

---

## Code Conventions

### Python Style

- **Formatter:** Ruff — single quotes, 99-char line length, space indentation
- **Linter:** Ruff — rules `C, D, E, F, I, W` (PEP 8 + docstrings + imports)
- **Docstrings:** Google convention (`tool.ruff.lint.pydocstyle.convention = "google"`)
- **Type checking:** Pyright in `basic` mode
- **Imports:** Sorted by `ruff.lint.isort` with `no-sections = true`, two blank lines after imports

### Naming

- Module-level constants: `UPPER_SNAKE_CASE` (e.g., `SYSTEM_MESSAGE`, `_PROVIDERS`)
- Private helpers: `_leading_underscore` (e.g., `_build_execution_namespace`, `_ensure_show_false`)
- Pydantic models: `PascalCase` with descriptive `Field(description=...)` on every field
- MCP tool functions: `mcp_` prefix for server tool wrappers (e.g., `mcp_generate_diagram`)
- Enums: `PascalCase` class, `UPPER_CASE` members (e.g., `DiagramType.AZURE`)

### Error Handling

- Return error responses via Pydantic models (`DiagramGenerateResponse(status='error', ...)`)
- MCP errors use `CallToolResult(isError=True, content=[TextContent(...)])`
- Security failures return descriptive messages identifying the specific issue
- Never raise exceptions from MCP tool functions — always return structured error responses

### File Headers

Every Python file starts with:
```python
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
```

Followed by a module-level docstring describing the file's purpose.

---

## MCP Server Details

### Tool Registration

Tools are registered with `@mcp.tool(name='...')` on the `FastMCP` instance. Each tool function uses `pydantic.Field` for parameter descriptions:

```python
@mcp.tool(name='generate_diagram')
async def mcp_generate_diagram(
    code: str = Field(..., description='Python code using the diagrams package DSL...'),
    filename: Optional[str] = Field(default=None, description='Optional output filename...'),
) -> CallToolResult:
```

### MCP Apps Integration

The `generate_diagram` tool returns `CallToolResult` with:
- `structuredContent` — JSON with `status`, `path`, `message`, `imageData` (base64 PNG)
- `_meta.ui.resourceUri` — Points to `ui://diagram-viewer/app.html` for the interactive viewer

The viewer (`viewer/app.html`) is served as an MCP resource and renders diagrams inline in MCP hosts with pan, zoom, download, and dark/light theme support.

### Server Instructions

The server includes an `instructions` string in its `FastMCP` config that tells LLMs the recommended workflow:
1. `list_icons` → discover available icons
2. `get_diagram_examples` → reference example code
3. `generate_diagram` → submit diagram code

---

## Copilot SDK Integration

### Module: `copilot_client.py`

Uses `github-copilot-sdk` Python package (`from copilot import CopilotClient`).

**Key components:**
- `DiagramCopilotClient` class — async context manager wrapping `CopilotClient`
- `SYSTEM_MESSAGE` — Instructs the LLM to act as an Azure Diagram Architect
- `DIAGRAM_ARCHITECT_AGENT` — Custom agent definition with name, description, prompt
- BYOK support via `DIAGRAM_COPILOT_*` environment variables
- Streaming via `on_delta` / `on_idle` event handlers
- Session persistence via `session_id` / `resume()`

**MCP Server connection:**
```python
session_config = {
    "model": "gpt-4.1",
    "mcpServers": {
        "azure-diagrams": {
            "type": "local",
            "command": "microsoft.azure-diagram-mcp-server",
            "args": [],
            "tools": ["*"],
        }
    },
    "customAgents": [DIAGRAM_ARCHITECT_AGENT],
    "tools": [describe_diagram],  # Custom tool defined with @define_tool
}
```

### Custom Tools

Custom tools use the `@define_tool` decorator with Pydantic parameter models:
```python
from copilot.tools import define_tool
from pydantic import BaseModel, Field

class MyParams(BaseModel):
    value: str = Field(description="Input value")

@define_tool(description="Process a value")
async def my_tool(params: MyParams) -> dict:
    return {"result": params.value}
```

### BYOK Environment Variables

| Variable | Description |
|----------|-------------|
| `DIAGRAM_COPILOT_PROVIDER_TYPE` | Provider: `openai`, `azure`, `anthropic` |
| `DIAGRAM_COPILOT_BASE_URL` | API endpoint URL |
| `DIAGRAM_COPILOT_API_KEY` | API key (from env, never hardcoded) |
| `DIAGRAM_COPILOT_WIRE_API` | Wire format: `completions` or `responses` |
| `DIAGRAM_COPILOT_AZURE_API_VERSION` | Azure API version (default: `2024-10-21`) |
| `DIAGRAM_COPILOT_MODEL` | Model override (default: `gpt-4.1`) |
| `DIAGRAM_COPILOT_WORKSPACE_DIR` | Workspace directory for diagram output |

---

## Security Scanner

### Threat Model

User-submitted Python code is executed server-side, so the scanner blocks:

| Category | Blocked Items |
|----------|---------------|
| **Dangerous builtins** | `exec`, `eval`, `compile`, `getattr`, `setattr`, `delattr`, `vars`, `__import__`, `breakpoint`, `open`, `globals`, `locals`, `spawn` |
| **Dangerous calls** | `os.system`, `os.popen`, `pickle.loads`, `pickle.load`, `subprocess.*` |
| **Dunder access** | `__dict__`, `__builtins__`, `__class__`, `__subclasses__`, `__bases__`, `__globals__`, `__mro__` |
| **Imports** | All `import` and `from ... import` statements |

Analysis uses AST parsing first, falling back to string-based detection if parsing fails.

---

## Testing

### Running Tests

```bash
# Full suite (140 tests, 9 skip without Graphviz)
uv run pytest tests/ -v

# Single test file
uv run pytest tests/test_copilot_client.py -v

# With coverage
uv run pytest --cov=microsoft --cov-report=term-missing tests/

# Quick check (stop on first failure)
uv run pytest tests/ -x -q
```

### Test Organization

| File | Tests | Coverage |
|------|-------|----------|
| `test_scanner.py` | 58 | AST analysis, dangerous functions, security checks, syntax validation |
| `test_copilot_client.py` | 37 | CopilotClient lifecycle, session config, BYOK, streaming, resume |
| `test_diagram_tools.py` | 28 | Diagram generation, examples, icon listing, code preprocessing |
| `test_server.py` | 15 | MCP tool wrappers, error handling, tool registration |
| `test_models.py` | 12 | Pydantic model validation, DiagramType enum, field constraints |

### Test Conventions

- **Mocking:** Use `unittest.mock.patch` to mock external dependencies (diagram generation, CopilotClient)
- **Async tests:** Use `@pytest.mark.asyncio` decorator (auto mode configured in `pyproject.toml`)
- **Fixtures:** Defined in `conftest.py` — `temp_workspace_dir`, `azure_diagram_code`, `dangerous_diagram_code`, etc.
- **Class-based:** Tests grouped in `class TestXxx:` with descriptive docstrings on each method
- **9 Graphviz-dependent tests** skip gracefully when Graphviz is not installed

### Writing New Tests

Follow TDD when adding new features:

1. Write the test first in the appropriate `test_*.py` file
2. Group related tests in a `class Test...` with a class-level docstring
3. Each test method gets a docstring explaining what it verifies
4. Mock external dependencies — never call real APIs or require network
5. Use existing fixtures from `conftest.py` where applicable

Example pattern:
```python
class TestMyFeature:
    """Tests for the my_feature function."""

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.module.dependency')
    async def test_success_case(self, mock_dep):
        """Verify correct result is returned on success."""
        mock_dep.return_value = expected_value
        result = await my_feature(input_data)
        assert result == expected_output
```

---

## Linting & Type Checking

```bash
# Lint (Ruff)
uv run ruff check microsoft/ tests/

# Auto-fix lint issues
uv run ruff check --fix microsoft/ tests/

# Format check
uv run ruff format --check microsoft/ tests/

# Auto-format
uv run ruff format microsoft/ tests/

# Type check (Pyright)
uv run pyright
```

### Ruff Configuration

Defined in `pyproject.toml`:
- Line length: 99
- Quote style: single quotes
- Import sorting: no sections, 2 blank lines after imports
- Selected rules: `C` (complexity), `D` (docstrings), `E` (pycodestyle), `F` (pyflakes), `I` (isort), `W` (warnings)
- Ignored: `C901` (complexity), `E501` (line length), `D100` (module docstring in `__init__.py`), `D106` (nested class docstring)

---

## CI/CD

### GitHub Actions Workflows

**`ci.yml`** — Runs on push/PR to `main`:
| Job | What it does |
|-----|--------------|
| **Lint** | `ruff check .` + `ruff format --check .` (Python 3.13) |
| **Type Check** | `pyright` (Python 3.13) |
| **Test** | `pytest -xvs --cov` (Python 3.12 + 3.13 matrix, with Graphviz installed) |

**`docs.yml`** — Runs on push to `main` when `docs-site/**` changes:
| Job | What it does |
|-----|--------------|
| **Build** | `npm ci` + `npm run docs:build` (Node.js 20) |
| **Deploy** | Uploads `.vitepress/dist` → GitHub Pages |

### Pre-commit Hooks

Configured in `.pre-commit-config.yaml`:
- **On commit:** trailing whitespace, EOF fixer, YAML/TOML check, large file check, private key detection, Ruff lint+format, Pyright
- **On push:** pytest (full test suite)

Setup: `pip install pre-commit && pre-commit install`

---

## GitHub Pages Documentation

### Site: VitePress

The documentation site lives in `docs-site/` and is deployed to GitHub Pages at `https://microsoft.github.io/diagrams-mcp-server/`.

**Stack:**
- VitePress with dark theme default
- Base path: `/diagrams-mcp-server/`
- Azure blue (#0078d4) branding

### Pages

| Path | Content |
|------|---------|
| `index.md` | Home — hero banner, 3 feature cards (Azure-First, Security, MCP Native) |
| `guide/getting-started.md` | Prerequisites, quick install, tool overview |
| `guide/installation.md` | System requirements, install methods (uv, pip, Docker) |
| `guide/examples.md` | Diagram examples with runnable code |

### Modifying Documentation

```bash
# Install docs dependencies
cd docs-site && npm install

# Local dev server with hot reload
npm run docs:dev

# Build for production
npm run docs:build

# Preview production build
npm run docs:preview
```

### VitePress Config (`docs-site/.vitepress/config.ts`)

- **Navigation:** Home, Guide, GitHub link
- **Sidebar:** Getting Started → Installation → Examples
- **Search:** Local search provider
- **Footer:** MIT License + Microsoft Corporation copyright

When adding new pages:
1. Create a `.md` file in `docs-site/guide/`
2. Add it to the `sidebar` array in `config.ts`
3. Optionally add to `nav` in `config.ts`

---

## Docker

### Building

```bash
docker build -t microsoft/azure-diagram-mcp-server .
```

### Architecture

Multi-stage build:
1. **Builder stage:** Python 3.13-slim, installs `uv`, syncs dependencies with `--frozen`
2. **Runtime stage:** Python 3.13-slim, installs Graphviz + procps, copies venv from builder

Security:
- Non-root `app` user
- No cache (`PIP_NO_CACHE_DIR=1`)
- Compiled bytecode (`UV_COMPILE_BYTECODE=1`)
- Health check via `docker-healthcheck.sh` (60s interval)

### MCP Client Configuration

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

---

## MCP Apps Viewer

The interactive viewer (`microsoft/azure_diagram_mcp_server/viewer/app.html`) is a standalone HTML5 application served as an MCP resource (`ui://diagram-viewer/app.html`).

**Features:**
- Pan (click-drag) and zoom (mouse wheel, +/- keys)
- Fit-to-view (0 key or toolbar button)
- Download PNG
- Dark/light theme toggle
- Loading spinner, empty state, error state
- MCP App SDK integration via esm.sh for receiving streaming diagram data

**When modifying the viewer:**
- It's a single-file HTML app with embedded CSS (~275 lines) and JS (~287 lines)
- The viewer receives `structuredContent` from `CallToolResult` containing `imageData` (base64 PNG)
- Test changes by running the MCP server in an MCP host that supports MCP Apps (VS Code Copilot)

---

## Adding New Diagram Providers

To add support for a new diagram provider:

1. **Add to `_PROVIDERS` list** in `diagram_tools.py` — this auto-imports all submodules
2. **Add examples** to `diagram_tools.py` — create a `_NEWPROVIDER_EXAMPLES` dict and add it to `type_map` in `get_diagram_examples()`
3. **Add `DiagramType` enum member** in `models.py`
4. **Add test fixtures** in `conftest.py`
5. **Add tests** in `test_diagram_tools.py`

---

## Common Tasks

### Add a new MCP tool

1. Define the tool function in `server.py` with `@mcp.tool(name='tool_name')`
2. Use `pydantic.Field` for all parameters with descriptions
3. Return `CallToolResult` for success/error
4. Add tests in `test_server.py`
5. Update `docs-site/guide/getting-started.md` with the new tool

### Add a Copilot SDK custom tool

1. Define a Pydantic `BaseModel` for parameters
2. Use `@define_tool(description="...")` decorator
3. Pass the tool to `session_config['tools']` in `copilot_client.py`
4. Add tests in `test_copilot_client.py`

### Modify security rules

1. Update `DANGEROUS_BUILTINS`, `DANGEROUS_ATTR_CALLS`, or `DANGEROUS_DUNDERS` in `scanner.py`
2. Add a fix suggestion in `get_fix_suggestion()`
3. Add tests in `test_scanner.py` — both AST-based and string-fallback paths

---

## Quick Reference

| Task | Command |
|------|---------|
| Install dependencies | `uv sync --group dev` |
| Run all tests | `uv run pytest tests/ -v` |
| Run specific tests | `uv run pytest tests/test_server.py -v` |
| Lint | `uv run ruff check microsoft/ tests/` |
| Format | `uv run ruff format microsoft/ tests/` |
| Type check | `uv run pyright` |
| Auto-fix lint | `uv run ruff check --fix microsoft/ tests/` |
| Run MCP server | `uv run microsoft.azure-diagram-mcp-server` |
| Run Copilot client | `uv run microsoft.azure-diagram-copilot` |
| Build docs locally | `cd docs-site && npm run docs:dev` |
| Build Docker image | `docker build -t microsoft/azure-diagram-mcp-server .` |
| Pre-commit setup | `pip install pre-commit && pre-commit install` |
