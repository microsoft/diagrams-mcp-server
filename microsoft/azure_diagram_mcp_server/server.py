# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Azure Diagram MCP Server implementation."""

import base64
import os
import sys
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from microsoft.azure_diagram_mcp_server.bicep_tools import (
    bicep_graph_to_diagram_code,
    parse_bicep_graph,
)
from microsoft.azure_diagram_mcp_server.diagram_tools import (
    generate_diagram,
    get_diagram_examples,
    list_diagram_icons,
)
from microsoft.azure_diagram_mcp_server.models import DiagramType
from pydantic import Field
from typing import Any, Optional


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


@mcp.resource(
    'ui://diagram-viewer/app.html',
    mime_type='text/html;profile=mcp-app',
    meta={
        'ui': {
            'csp': {
                'resourceDomains': ['https://esm.sh'],
                'connectDomains': ['https://esm.sh'],
            }
        }
    },
)
def get_diagram_viewer() -> str:
    """Serve the interactive diagram viewer HTML app."""
    with open(VIEWER_HTML_PATH) as f:
        return f.read()


def _coerce_diagram_inputs(
    filename: Optional[str],
    timeout: int,
    workspace_dir: Optional[str],
    output_format: str,
) -> tuple[Optional[str], int, Optional[str], str]:
    """Normalize diagram tool inputs."""
    if not isinstance(filename, str):
        filename = None
    if not isinstance(timeout, int):
        timeout = 90
    if not isinstance(workspace_dir, str):
        workspace_dir = None
    if not isinstance(output_format, str):
        output_format = 'png'
    return filename, timeout, workspace_dir, output_format


def _extract_render_payload(path: Optional[str]) -> tuple[str, str, str]:
    """Read rendered diagram output and return format-specific payload fields."""
    image_data = ''
    svg_data = ''
    render_format = 'png'
    if path and os.path.exists(path):
        if path.lower().endswith('.svg'):
            render_format = 'svg'
            with open(path, encoding='utf-8') as f:
                svg_data = f.read()
        else:
            with open(path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
    return render_format, image_data, svg_data


def _build_graph_diff(
    graph_model: dict[str, Any],
    previous_graph_model: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Build a simple added/removed diff between two graph models."""
    resources = (
        graph_model.get('resources', []) if isinstance(graph_model.get('resources'), list) else []
    )
    previous_resources = (
        previous_graph_model.get('resources', [])
        if isinstance(previous_graph_model.get('resources'), list)
        else []
    )
    edges = graph_model.get('edges', []) if isinstance(graph_model.get('edges'), list) else []
    previous_edges = (
        previous_graph_model.get('edges', [])
        if isinstance(previous_graph_model.get('edges'), list)
        else []
    )

    previous_resource_keys = {
        (resource.get('symbolicName'), resource.get('resourceType'))
        for resource in previous_resources
    }
    resource_keys = {
        (resource.get('symbolicName'), resource.get('resourceType')) for resource in resources
    }
    previous_edge_keys = {
        (edge.get('from'), edge.get('to'), edge.get('kind', 'dependsOn'))
        for edge in previous_edges
    }
    edge_keys = {
        (edge.get('from'), edge.get('to'), edge.get('kind', 'dependsOn')) for edge in edges
    }

    return {
        'addedResources': [
            resource
            for resource in resources
            if (resource.get('symbolicName'), resource.get('resourceType'))
            not in previous_resource_keys
        ],
        'removedResources': [
            resource
            for resource in previous_resources
            if (resource.get('symbolicName'), resource.get('resourceType')) not in resource_keys
        ],
        'addedEdges': [
            edge
            for edge in edges
            if (edge.get('from'), edge.get('to'), edge.get('kind', 'dependsOn'))
            not in previous_edge_keys
        ],
        'removedEdges': [
            edge
            for edge in previous_edges
            if (edge.get('from'), edge.get('to'), edge.get('kind', 'dependsOn')) not in edge_keys
        ],
    }


def _normalize_graph_model(graph_model: dict[str, Any]) -> dict[str, Any]:
    """Normalize graph model payloads consumed by app-only edit tools."""
    resources: list[dict[str, Any]] = []
    raw_resources = graph_model.get('resources', []) if isinstance(graph_model, dict) else []
    if isinstance(raw_resources, list):
        for resource in raw_resources:
            if not isinstance(resource, dict):
                continue
            symbolic_name = resource.get('symbolicName')
            resource_type = resource.get('resourceType')
            if not isinstance(symbolic_name, str) or not symbolic_name.strip():
                continue
            if not isinstance(resource_type, str) or not resource_type.strip():
                continue
            normalized_resource = dict(resource)
            normalized_resource['symbolicName'] = symbolic_name.strip()
            normalized_resource['resourceType'] = resource_type.strip()
            resources.append(normalized_resource)

    edges: list[dict[str, Any]] = []
    raw_edges = graph_model.get('edges', []) if isinstance(graph_model, dict) else []
    if isinstance(raw_edges, list):
        for edge in raw_edges:
            if not isinstance(edge, dict):
                continue
            source = edge.get('from')
            target = edge.get('to')
            if not isinstance(source, str) or not source.strip():
                continue
            if not isinstance(target, str) or not target.strip():
                continue
            normalized_edge = dict(edge)
            normalized_edge['from'] = source.strip()
            normalized_edge['to'] = target.strip()
            edge_kind = edge.get('kind')
            normalized_edge['kind'] = (
                edge_kind.strip()
                if isinstance(edge_kind, str) and edge_kind.strip()
                else 'dependsOn'
            )
            edges.append(normalized_edge)

    symbols = {resource.get('symbolicName') for resource in resources}
    unresolved_dependencies = sorted(
        {edge.get('from') for edge in edges if edge.get('from') not in symbols}
    )
    status = graph_model.get('status') if isinstance(graph_model.get('status'), str) else 'success'
    message = graph_model.get('message') if isinstance(graph_model.get('message'), str) else ''
    return {
        'status': status,
        'message': message,
        'resources': resources,
        'edges': edges,
        'unresolvedDependencies': unresolved_dependencies,
    }


def _normalize_selected_component(
    selected_component: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Normalize selected component payloads used by edit intent tools."""
    if not isinstance(selected_component, dict):
        return None

    component_kind = selected_component.get('componentKind')
    if not isinstance(component_kind, str):
        return None
    component_kind = component_kind.strip().lower()

    if component_kind == 'resource':
        symbolic_name = selected_component.get('symbolicName')
        if not isinstance(symbolic_name, str) or not symbolic_name.strip():
            return None
        return {'componentKind': 'resource', 'symbolicName': symbolic_name.strip()}

    if component_kind == 'edge':
        source = selected_component.get('from')
        target = selected_component.get('to')
        if not isinstance(source, str) or not source.strip():
            return None
        if not isinstance(target, str) or not target.strip():
            return None
        edge_kind = selected_component.get('edgeKind')
        normalized_kind = (
            edge_kind.strip() if isinstance(edge_kind, str) and edge_kind.strip() else 'dependsOn'
        )
        return {
            'componentKind': 'edge',
            'from': source.strip(),
            'to': target.strip(),
            'edgeKind': normalized_kind,
        }

    return None


def _resolve_selected_component(
    graph_model: dict[str, Any],
    selection_intent: dict[str, Any],
) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]], Optional[str]]:
    """Resolve selection intent against the current graph model."""
    if not isinstance(selection_intent, dict):
        return None, None, 'selection_intent must be an object.'

    component_kind = selection_intent.get('componentKind')
    if not isinstance(component_kind, str):
        return None, None, 'selection_intent.componentKind must be "resource" or "edge".'
    component_kind = component_kind.strip().lower()

    if component_kind == 'resource':
        symbolic_name = selection_intent.get('symbolicName')
        if not isinstance(symbolic_name, str) or not symbolic_name.strip():
            return None, None, 'selection_intent.symbolicName is required for resource selection.'
        normalized_selection = {'componentKind': 'resource', 'symbolicName': symbolic_name.strip()}
        selected_resource = next(
            (
                resource
                for resource in graph_model.get('resources', [])
                if resource.get('symbolicName') == normalized_selection['symbolicName']
            ),
            None,
        )
        return normalized_selection, selected_resource, None

    if component_kind == 'edge':
        source = selection_intent.get('from')
        target = selection_intent.get('to')
        if not isinstance(source, str) or not source.strip():
            return None, None, 'selection_intent.from is required for edge selection.'
        if not isinstance(target, str) or not target.strip():
            return None, None, 'selection_intent.to is required for edge selection.'
        edge_kind = selection_intent.get('edgeKind')
        normalized_kind = (
            edge_kind.strip() if isinstance(edge_kind, str) and edge_kind.strip() else 'dependsOn'
        )
        normalized_selection = {
            'componentKind': 'edge',
            'from': source.strip(),
            'to': target.strip(),
            'edgeKind': normalized_kind,
        }
        selected_edge = next(
            (
                edge
                for edge in graph_model.get('edges', [])
                if edge.get('from') == normalized_selection['from']
                and edge.get('to') == normalized_selection['to']
                and edge.get('kind', 'dependsOn') == normalized_selection['edgeKind']
            ),
            None,
        )
        return normalized_selection, selected_edge, None

    return None, None, 'selection_intent.componentKind must be "resource" or "edge".'


def _sync_resource_dependencies(
    resources: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> None:
    """Synchronize resource dependsOn arrays from normalized edge data."""
    resources_by_symbol = {
        resource.get('symbolicName'): resource
        for resource in resources
        if isinstance(resource.get('symbolicName'), str)
    }
    for resource in resources:
        resource['dependsOn'] = []
    for edge in edges:
        source = edge.get('from')
        target = edge.get('to')
        if target in resources_by_symbol and isinstance(source, str) and source:
            depends_on = resources_by_symbol[target].setdefault('dependsOn', [])
            if source not in depends_on:
                depends_on.append(source)
    for resource in resources:
        depends_on = resource.get('dependsOn', [])
        if not isinstance(depends_on, list):
            resource['dependsOn'] = []
            continue
        resource['dependsOn'] = sorted(
            {
                dep.strip()
                for dep in (str(dependency) for dependency in depends_on)
                if isinstance(dep, str) and dep.strip()
            }
        )


def _dedupe_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return edges with duplicate from/to/kind triples removed."""
    deduped_edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    for edge in edges:
        source = edge.get('from')
        target = edge.get('to')
        edge_kind = edge.get('kind', 'dependsOn')
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        if not isinstance(edge_kind, str):
            edge_kind = 'dependsOn'
        edge_key = (source, target, edge_kind)
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        deduped_edges.append({'from': source, 'to': target, 'kind': edge_kind})
    return deduped_edges


def _apply_graph_edit_intent(
    graph_model: dict[str, Any],
    edit_intent: dict[str, Any],
    selected_component: Optional[dict[str, Any]] = None,
) -> tuple[dict[str, Any], dict[str, Any], Optional[str]]:
    """Apply a deterministic edit intent to a graph model."""
    normalized_graph = _normalize_graph_model(graph_model)
    if normalized_graph.get('status') != 'success':
        return normalized_graph, {}, 'graph_model.status must be "success" to apply edits.'
    if not isinstance(edit_intent, dict):
        return normalized_graph, {}, 'edit_intent must be an object.'

    action = edit_intent.get('action')
    if not isinstance(action, str) or not action.strip():
        return normalized_graph, {}, 'edit_intent.action is required.'
    action = action.strip().lower()
    normalized_intent: dict[str, Any] = {'action': action}

    resources = [dict(resource) for resource in normalized_graph.get('resources', [])]
    edges = [dict(edge) for edge in normalized_graph.get('edges', [])]
    normalized_selection = _normalize_selected_component(selected_component)

    symbolic_name = edit_intent.get('symbolicName')
    if not isinstance(symbolic_name, str) or not symbolic_name.strip():
        symbolic_name = (
            normalized_selection.get('symbolicName')
            if isinstance(normalized_selection, dict)
            and normalized_selection.get('componentKind') == 'resource'
            else None
        )
    symbolic_name = symbolic_name.strip() if isinstance(symbolic_name, str) else None

    if action == 'add_resource':
        resource_payload = edit_intent.get('resource')
        if not isinstance(resource_payload, dict):
            return (
                normalized_graph,
                normalized_intent,
                'edit_intent.resource is required for add_resource.',
            )
        resource_symbol = resource_payload.get('symbolicName')
        resource_type = resource_payload.get('resourceType')
        if not isinstance(resource_symbol, str) or not resource_symbol.strip():
            return normalized_graph, normalized_intent, 'resource.symbolicName is required.'
        if not isinstance(resource_type, str) or not resource_type.strip():
            return normalized_graph, normalized_intent, 'resource.resourceType is required.'
        resource_symbol = resource_symbol.strip()
        resource_type = resource_type.strip()
        if any(resource.get('symbolicName') == resource_symbol for resource in resources):
            return (
                normalized_graph,
                normalized_intent,
                f'Resource "{resource_symbol}" already exists in graph_model.resources.',
            )
        resources.append(
            {'symbolicName': resource_symbol, 'resourceType': resource_type, 'dependsOn': []}
        )
        depends_on_payload = resource_payload.get('dependsOn')
        depends_on_values: list[str] = []
        if isinstance(depends_on_payload, list):
            for dependency in depends_on_payload:
                dependency_name = str(dependency).strip()
                if dependency_name and dependency_name not in depends_on_values:
                    depends_on_values.append(dependency_name)
        for dependency_name in depends_on_values:
            edges.append({'from': dependency_name, 'to': resource_symbol, 'kind': 'dependsOn'})
        normalized_intent['resource'] = {
            'symbolicName': resource_symbol,
            'resourceType': resource_type,
            'dependsOn': depends_on_values,
        }

    elif action == 'remove_resource':
        if not symbolic_name:
            return (
                normalized_graph,
                normalized_intent,
                'edit_intent.symbolicName is required for remove_resource.',
            )
        if not any(resource.get('symbolicName') == symbolic_name for resource in resources):
            return (
                normalized_graph,
                normalized_intent,
                f'Resource "{symbolic_name}" was not found.',
            )
        resources = [
            resource for resource in resources if resource.get('symbolicName') != symbolic_name
        ]
        edges = [
            edge
            for edge in edges
            if edge.get('from') != symbolic_name and edge.get('to') != symbolic_name
        ]
        normalized_intent['symbolicName'] = symbolic_name

    elif action == 'set_resource_type':
        resource_type = edit_intent.get('resourceType')
        if not symbolic_name:
            return (
                normalized_graph,
                normalized_intent,
                'edit_intent.symbolicName is required for set_resource_type.',
            )
        if not isinstance(resource_type, str) or not resource_type.strip():
            return (
                normalized_graph,
                normalized_intent,
                'edit_intent.resourceType is required for set_resource_type.',
            )
        resource_type = resource_type.strip()
        target_resource = next(
            (resource for resource in resources if resource.get('symbolicName') == symbolic_name),
            None,
        )
        if target_resource is None:
            return (
                normalized_graph,
                normalized_intent,
                f'Resource "{symbolic_name}" was not found.',
            )
        target_resource['resourceType'] = resource_type
        normalized_intent['symbolicName'] = symbolic_name
        normalized_intent['resourceType'] = resource_type

    elif action == 'rename_resource':
        new_symbolic_name = edit_intent.get('newSymbolicName')
        if not symbolic_name:
            return (
                normalized_graph,
                normalized_intent,
                'edit_intent.symbolicName is required for rename_resource.',
            )
        if not isinstance(new_symbolic_name, str) or not new_symbolic_name.strip():
            return (
                normalized_graph,
                normalized_intent,
                'edit_intent.newSymbolicName is required for rename_resource.',
            )
        new_symbolic_name = new_symbolic_name.strip()
        if any(
            resource.get('symbolicName') == new_symbolic_name
            and resource.get('symbolicName') != symbolic_name
            for resource in resources
        ):
            return (
                normalized_graph,
                normalized_intent,
                f'Resource "{new_symbolic_name}" already exists in graph_model.resources.',
            )
        renamed = False
        for resource in resources:
            if resource.get('symbolicName') == symbolic_name:
                resource['symbolicName'] = new_symbolic_name
                renamed = True
        if not renamed:
            return (
                normalized_graph,
                normalized_intent,
                f'Resource "{symbolic_name}" was not found.',
            )
        for edge in edges:
            if edge.get('from') == symbolic_name:
                edge['from'] = new_symbolic_name
            if edge.get('to') == symbolic_name:
                edge['to'] = new_symbolic_name
        normalized_intent['symbolicName'] = symbolic_name
        normalized_intent['newSymbolicName'] = new_symbolic_name

    elif action in {'add_dependency', 'remove_dependency'}:
        edge_from = edit_intent.get('from')
        edge_to = edit_intent.get('to')
        if not isinstance(edge_from, str) or not edge_from.strip():
            edge_from = (
                normalized_selection.get('from')
                if isinstance(normalized_selection, dict)
                and normalized_selection.get('componentKind') == 'edge'
                else None
            )
        if not isinstance(edge_to, str) or not edge_to.strip():
            edge_to = (
                normalized_selection.get('to')
                if isinstance(normalized_selection, dict)
                and normalized_selection.get('componentKind') == 'edge'
                else symbolic_name
            )
        if not isinstance(edge_from, str) or not edge_from.strip():
            return (
                normalized_graph,
                normalized_intent,
                'edit_intent.from is required for dependency edits.',
            )
        if not isinstance(edge_to, str) or not edge_to.strip():
            return (
                normalized_graph,
                normalized_intent,
                'edit_intent.to is required for dependency edits.',
            )
        edge_from = edge_from.strip()
        edge_to = edge_to.strip()
        edge_kind = edit_intent.get('edgeKind')
        if not isinstance(edge_kind, str) or not edge_kind.strip():
            edge_kind = 'dependsOn'
        edge_kind = edge_kind.strip()
        edge_key = (edge_from, edge_to, edge_kind)
        normalized_intent.update({'from': edge_from, 'to': edge_to, 'edgeKind': edge_kind})
        if action == 'add_dependency':
            if not any(
                (edge.get('from'), edge.get('to'), edge.get('kind', 'dependsOn')) == edge_key
                for edge in edges
            ):
                edges.append({'from': edge_from, 'to': edge_to, 'kind': edge_kind})
        else:
            edges = [
                edge
                for edge in edges
                if (edge.get('from'), edge.get('to'), edge.get('kind', 'dependsOn')) != edge_key
            ]

    else:
        return (
            normalized_graph,
            normalized_intent,
            (
                'Unsupported edit_intent.action. Supported values: add_resource, remove_resource, '
                'set_resource_type, rename_resource, add_dependency, remove_dependency.'
            ),
        )

    edges = _dedupe_edges(edges)
    _sync_resource_dependencies(resources, edges)
    symbols = {resource.get('symbolicName') for resource in resources}
    unresolved_dependencies = sorted(
        {edge.get('from') for edge in edges if edge.get('from') not in symbols}
    )
    updated_graph = {
        'status': 'success',
        'message': f'Applied edit action "{action}".',
        'resources': resources,
        'edges': edges,
        'unresolvedDependencies': unresolved_dependencies,
    }
    return updated_graph, normalized_intent, None


async def _generate_bicep_diagram(
    bicep_code: str,
    filename: Optional[str],
    timeout: int,
    workspace_dir: Optional[str],
    output_format: str,
    previous_graph_model: Optional[dict[str, Any]] = None,
) -> CallToolResult:
    """Parse Bicep, generate diagrams code, and render output."""
    filename, timeout, workspace_dir, output_format = _coerce_diagram_inputs(
        filename, timeout, workspace_dir, output_format
    )
    graph_model = parse_bicep_graph(bicep_code)
    graph_diff = (
        _build_graph_diff(graph_model, previous_graph_model)
        if isinstance(previous_graph_model, dict) and graph_model.get('status') == 'success'
        else None
    )

    if graph_model.get('status') != 'success':
        structured_content: dict[str, Any] = {
            'status': 'error',
            'path': None,
            'message': graph_model.get('message', 'Failed to parse Bicep source.'),
            'renderFormat': 'png',
            'imageData': '',
            'svgData': '',
            'graphModel': graph_model,
        }
        if graph_diff is not None:
            structured_content['graphDiff'] = graph_diff
        return CallToolResult(
            content=[TextContent(type='text', text=f'Error: {structured_content["message"]}')],
            structuredContent=structured_content,
            isError=True,
        )

    diagram_code = bicep_graph_to_diagram_code(graph_model)
    result = await generate_diagram(
        diagram_code, filename, timeout or 90, workspace_dir, output_format
    )

    render_format, image_data, svg_data = _extract_render_payload(result.path)
    structured_content = {
        'status': result.status,
        'path': result.path,
        'message': result.message,
        'renderFormat': render_format,
        'imageData': image_data,
        'svgData': svg_data,
        'graphModel': graph_model,
    }
    if graph_diff is not None:
        structured_content['graphDiff'] = graph_diff

    if result.status == 'error':
        return CallToolResult(
            content=[TextContent(type='text', text=f'Error: {result.message}')],
            structuredContent=structured_content,
            isError=True,
        )

    return CallToolResult(
        content=[TextContent(type='text', text=result.message)],
        structuredContent=structured_content,
        _meta={'ui': {'resourceUri': 'ui://diagram-viewer/app.html'}},
    )


@mcp.tool(
    name='generate_diagram',
    meta={'ui': {'resourceUri': 'ui://diagram-viewer/app.html'}},
)
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
    output_format: str = Field(
        default='png',
        description='Output render format for the diagram. Supported values: png, svg.',
    ),
) -> CallToolResult:
    """Generate a diagram from Python code using the diagrams package DSL."""
    if not isinstance(filename, str):
        filename = None
    if not isinstance(timeout, int):
        timeout = 90
    if not isinstance(workspace_dir, str):
        workspace_dir = None
    if not isinstance(output_format, str):
        output_format = 'png'

    result = await generate_diagram(code, filename, timeout or 90, workspace_dir, output_format)

    if result.status == 'error':
        return CallToolResult(
            content=[TextContent(type='text', text=f'Error: {result.message}')],
            isError=True,
        )

    image_data = ''
    svg_data = ''
    render_format = 'png'
    if result.path and os.path.exists(result.path):
        if result.path.lower().endswith('.svg'):
            render_format = 'svg'
            with open(result.path, encoding='utf-8') as f:
                svg_data = f.read()
        else:
            with open(result.path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

    return CallToolResult(
        content=[TextContent(type='text', text=result.message)],
        structuredContent={
            'status': result.status,
            'path': result.path,
            'message': result.message,
            'renderFormat': render_format,
            'imageData': image_data,
            'svgData': svg_data,
        },
        _meta={'ui': {'resourceUri': 'ui://diagram-viewer/app.html'}},
    )


@mcp.tool(
    name='refresh_diagram',
    meta={'ui': {'visibility': ['app']}},
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
    output_format: str = Field(
        default='png',
        description='Output render format for the diagram. Supported values: png, svg.',
    ),
) -> CallToolResult:
    """Regenerate a diagram from updated code (app-only tool)."""
    return await mcp_generate_diagram(code, filename, timeout, workspace_dir, output_format)


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


@mcp.tool(name='preview_bicep_graph')
async def mcp_preview_bicep_graph(
    bicep_code: str = Field(
        ...,
        description='Bicep source code to parse into a resource/dependency graph preview.',
    ),
):
    """Preview a resource graph extracted from Bicep source."""
    return parse_bicep_graph(bicep_code)


@mcp.tool(
    name='generate_diagram_from_bicep',
    meta={'ui': {'resourceUri': 'ui://diagram-viewer/app.html'}},
)
async def mcp_generate_diagram_from_bicep(
    bicep_code: str = Field(
        ...,
        description='Bicep source code to parse and render as a diagram.',
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
    output_format: str = Field(
        default='png',
        description='Output render format for the diagram. Supported values: png, svg.',
    ),
) -> CallToolResult:
    """Generate a diagram directly from Bicep source code."""
    return await _generate_bicep_diagram(
        bicep_code=bicep_code,
        filename=filename,
        timeout=timeout,
        workspace_dir=workspace_dir,
        output_format=output_format,
    )


@mcp.tool(
    name='update_diagram_from_bicep',
    meta={'ui': {'resourceUri': 'ui://diagram-viewer/app.html'}},
)
async def mcp_update_diagram_from_bicep(
    bicep_code: str = Field(
        ...,
        description='Updated Bicep source code to parse and render as a diagram.',
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
    output_format: str = Field(
        default='png',
        description='Output render format for the diagram. Supported values: png, svg.',
    ),
    previous_graph_model: Optional[dict[str, Any]] = Field(
        default=None,
        description='Optional previous graph model used to compute graphDiff.',
    ),
) -> CallToolResult:
    """Update a Bicep-based diagram and include graphDiff when previous model is provided."""
    return await _generate_bicep_diagram(
        bicep_code=bicep_code,
        filename=filename,
        timeout=timeout,
        workspace_dir=workspace_dir,
        output_format=output_format,
        previous_graph_model=previous_graph_model,
    )


@mcp.tool(
    name='select_component',
    meta={'ui': {'visibility': ['app']}},
)
async def mcp_select_component(
    graph_model: dict[str, Any] = Field(
        ...,
        description='Current resource graph model payload with resources and edges.',
    ),
    selection_intent: dict[str, Any] = Field(
        ...,
        description=(
            'Selection intent payload. Use {"componentKind":"resource","symbolicName":"..."} '
            'or {"componentKind":"edge","from":"...","to":"...","edgeKind":"dependsOn"}.'
        ),
    ),
):
    """Resolve a resource or edge selection for app-side edit intent workflows."""
    normalized_graph = _normalize_graph_model(graph_model)
    selected_component, component, error_message = _resolve_selected_component(
        normalized_graph, selection_intent
    )
    if error_message:
        return {
            'status': 'error',
            'message': error_message,
            'selectedComponent': selected_component,
            'component': None,
            'found': False,
        }
    return {
        'status': 'success',
        'message': 'Component selected.' if component is not None else 'Component not found.',
        'selectedComponent': selected_component,
        'component': component,
        'found': component is not None,
    }


@mcp.tool(
    name='preview_edit',
    meta={'ui': {'visibility': ['app']}},
)
async def mcp_preview_edit(
    graph_model: dict[str, Any] = Field(
        ...,
        description='Current graph model payload to preview edit intents against.',
    ),
    edit_intent: dict[str, Any] = Field(
        ...,
        description='Edit intent payload describing a deterministic graph update action.',
    ),
    selected_component: Optional[dict[str, Any]] = Field(
        default=None,
        description='Optional selected component payload returned by select_component.',
    ),
):
    """Preview deterministic graph changes for host-side Bicep edit roundtrips."""
    previous_graph_model = _normalize_graph_model(graph_model)
    normalized_selected = _normalize_selected_component(selected_component)
    next_graph_model, normalized_intent, error_message = _apply_graph_edit_intent(
        previous_graph_model, edit_intent, normalized_selected
    )
    graph_diff = _build_graph_diff(next_graph_model, previous_graph_model)
    if error_message:
        return {
            'status': 'error',
            'message': error_message,
            'selectedComponent': normalized_selected,
            'editIntent': normalized_intent,
            'graphDiff': graph_diff,
        }
    return {
        'status': 'success',
        'message': 'Preview generated.',
        'selectedComponent': normalized_selected,
        'editIntent': normalized_intent,
        'graphDiff': graph_diff,
    }


@mcp.tool(
    name='apply_edit',
    meta={'ui': {'visibility': ['app']}},
)
async def mcp_apply_edit(
    graph_model: dict[str, Any] = Field(
        ...,
        description='Current graph model payload to update.',
    ),
    edit_intent: dict[str, Any] = Field(
        ...,
        description='Edit intent payload describing a deterministic graph update action.',
    ),
    selected_component: Optional[dict[str, Any]] = Field(
        default=None,
        description='Optional selected component payload returned by select_component.',
    ),
):
    """Apply deterministic graph edits for host-side Bicep roundtrip workflows."""
    previous_graph_model = _normalize_graph_model(graph_model)
    normalized_selected = _normalize_selected_component(selected_component)
    next_graph_model, normalized_intent, error_message = _apply_graph_edit_intent(
        previous_graph_model, edit_intent, normalized_selected
    )
    graph_diff = _build_graph_diff(next_graph_model, previous_graph_model)
    if error_message:
        return {
            'status': 'error',
            'message': error_message,
            'selectedComponent': normalized_selected,
            'editIntent': normalized_intent,
            'graphDiff': graph_diff,
            'graphModel': previous_graph_model,
        }
    return {
        'status': 'success',
        'message': 'Edit applied.',
        'selectedComponent': normalized_selected,
        'editIntent': normalized_intent,
        'graphDiff': graph_diff,
        'graphModel': next_graph_model,
    }


@mcp.tool(
    name='report_diagram_interaction',
    meta={'ui': {'visibility': ['app']}},
)
async def mcp_report_diagram_interaction(
    event_type: str = Field(
        ..., description='Interaction type, e.g. select, drag_start, drag_end.'
    ),
    element_id: Optional[str] = Field(
        default=None,
        description='Optional selected diagram element ID emitted by the viewer.',
    ),
    element_kind: Optional[str] = Field(
        default=None,
        description='Optional element kind, e.g. node or edge.',
    ),
):
    """Receive app-only interaction events from the diagram viewer."""
    return {
        'status': 'success',
        'eventType': event_type,
        'elementId': element_id,
        'elementKind': element_kind,
    }


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
