# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Azure Diagram MCP Server implementation."""

import base64
import os
import sys
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from microsoft.azure_diagram_mcp_server.diagram_tools import (
    generate_diagram,
    get_diagram_examples,
    list_diagram_icons,
)
from microsoft.azure_diagram_mcp_server.models import DiagramType
from pydantic import Field
from typing import Optional


VIEWER_HTML_PATH = os.path.join(os.path.dirname(__file__), 'viewer', 'app.html')

mcp = FastMCP(
    'azure-diagram-mcp-server',
    dependencies=['pydantic', 'diagrams'],
    log_level='ERROR',
    instructions="""Azure Diagram MCP Server - Generate infrastructure and architecture diagrams.

Workflow:
1. Use list_icons to discover available icons and providers for your diagrams.
2. Use get_diagram_examples to get example code for the diagram type you want to create.
3. Use generate_diagram to submit Python code using the diagrams package DSL to generate diagrams.

Supported diagram types: Azure architecture, sequence, flow, class, Kubernetes (K8s), on-premises, and custom diagrams.

This server is designed for Azure and Microsoft infrastructure diagramming. Use Azure/Microsoft services and icons when building cloud architecture diagrams.""",
)


@mcp.resource('ui://diagram-viewer/app.html')
def get_diagram_viewer() -> str:
    """Serve the interactive diagram viewer HTML app."""
    with open(VIEWER_HTML_PATH) as f:
        return f.read()


@mcp.tool(name='generate_diagram')
async def mcp_generate_diagram(
    code: str = Field(
        ...,
        description='Python code using the diagrams package DSL to generate a diagram. Must contain a Diagram() call.',
    ),
    filename: Optional[str] = Field(
        default=None,
        description='Optional output filename for the generated diagram (without extension).',
    ),
    timeout: int = Field(
        default=90,
        description='Timeout in seconds for diagram generation (1-300).',
    ),
    workspace_dir: Optional[str] = Field(
        default=None,
        description='Optional workspace directory for output files.',
    ),
) -> CallToolResult:
    """Generate a diagram from Python code using the diagrams package DSL."""
    result = await generate_diagram(code, filename, timeout or 90, workspace_dir)

    if result.status == 'error':
        return CallToolResult(
            content=[TextContent(type='text', text=f'Error: {result.message}')],
            isError=True,
        )

    image_data = ''
    if result.path and os.path.exists(result.path):
        with open(result.path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

    return CallToolResult(
        content=[TextContent(type='text', text=result.message)],
        structuredContent={
            'status': result.status,
            'path': result.path,
            'message': result.message,
            'imageData': image_data,
        },
        _meta={'ui': {'resourceUri': 'ui://diagram-viewer/app.html'}},
    )


@mcp.tool(
    name='refresh_diagram',
    annotations={'_meta': {'ui': {'visibility': ['app']}}},
)
async def mcp_refresh_diagram(
    code: str = Field(
        ...,
        description='Python code using the diagrams package DSL to regenerate a diagram.',
    ),
    filename: Optional[str] = Field(
        default=None,
        description='Optional output filename for the generated diagram (without extension).',
    ),
    timeout: int = Field(
        default=90,
        description='Timeout in seconds for diagram generation (1-300).',
    ),
    workspace_dir: Optional[str] = Field(
        default=None,
        description='Optional workspace directory for output files.',
    ),
) -> CallToolResult:
    """Regenerate a diagram from updated code (app-only tool)."""
    return await mcp_generate_diagram(code, filename, timeout, workspace_dir)


@mcp.tool(name='get_diagram_examples')
async def mcp_get_diagram_examples(
    diagram_type: str = Field(
        default='all',
        description='The type of diagram examples to retrieve. Options: azure, sequence, flow, class, k8s, onprem, custom, all.',
    ),
):
    """Get example diagram code for the specified diagram type."""
    try:
        dt = DiagramType(diagram_type.lower())
    except ValueError:
        dt = DiagramType.ALL
    result = get_diagram_examples(dt)
    return result.model_dump()


@mcp.tool(name='list_icons')
async def mcp_list_diagram_icons(
    provider_filter: Optional[str] = Field(
        default=None,
        description='Optional filter to narrow results by provider name (e.g. azure, k8s, onprem).',
    ),
    service_filter: Optional[str] = Field(
        default=None,
        description='Optional filter to narrow results by service name (e.g. compute, database, network).',
    ),
):
    """List available diagram icons organized by provider and service."""
    result = list_diagram_icons(provider_filter, service_filter)
    return result.model_dump()


def main():
    """Run the MCP server with CLI argument support."""
    if '--help' in sys.argv or '-h' in sys.argv:
        print('Azure Diagram MCP Server v0.1.1')
        print()
        print('An MCP server for generating professional infrastructure diagrams.')
        print()
        print('Usage:')
        print('  This is an MCP stdio server — it communicates via JSON-RPC over')
        print('  stdin/stdout and is meant to be launched by an MCP client.')
        print()
        print('  Copilot CLI:  /mcp add → Command: uvx microsoft.azure-diagram-mcp-server')
        print('  VS Code:      Add to settings.json under mcp.servers')
        print()
        print('  See: https://github.com/microsoft/diagrams-mcp-server#getting-started')
        sys.exit(0)

    if '--version' in sys.argv or '-v' in sys.argv:
        print('microsoft.azure-diagram-mcp-server 0.1.1')
        sys.exit(0)

    if sys.stdin.isatty():
        print('Azure Diagram MCP Server v0.1.1')
        print()
        print('⚠  This is an MCP stdio server — do not run it directly.')
        print('   It communicates via JSON-RPC over stdin/stdout and must be')
        print('   launched by an MCP client (Copilot CLI, VS Code, etc).')
        print()
        print('Quick setup:')
        print(
            '  Copilot CLI:  copilot → /mcp add → Command: uvx microsoft.azure-diagram-mcp-server'
        )
        print('  VS Code:      Add to settings.json under mcp.servers')
        print()
        print('Run with --help for more info.')
        sys.exit(1)

    mcp.run()


if __name__ == '__main__':
    main()
