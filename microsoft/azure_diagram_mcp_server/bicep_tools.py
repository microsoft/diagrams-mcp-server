# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Bicep parsing helpers for graph preview and diagram generation workflows."""

import keyword
import re
from typing import Any


_RESOURCE_DECL_RE = re.compile(
    r"^\s*resource\s+(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)\s+'(?P<type>[^'@]+)@[^']+'\s*=\s*\{"
)
_DEPENDS_ON_RE = re.compile(r'dependsOn\s*:\s*\[(?P<deps>[^\]]*)\]', re.S)
_SYMBOL_RE = re.compile(r'\b([A-Za-z_][A-Za-z0-9_]*)\b')


def _extract_resource_blocks(bicep_code: str) -> list[dict[str, Any]]:
    """Extract resource blocks with their symbolic names and types."""
    lines = bicep_code.splitlines()
    blocks: list[dict[str, Any]] = []
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        match = _RESOURCE_DECL_RE.match(line)
        if not match:
            idx += 1
            continue

        start_idx = idx
        brace_depth = line.count('{') - line.count('}')
        block_lines = [line]
        idx += 1

        while idx < len(lines) and brace_depth > 0:
            next_line = lines[idx]
            block_lines.append(next_line)
            brace_depth += next_line.count('{') - next_line.count('}')
            idx += 1

        blocks.append(
            {
                'symbolicName': match.group('symbol'),
                'resourceType': match.group('type'),
                'line': start_idx + 1,
                'blockText': '\n'.join(block_lines),
            }
        )

    return blocks


def parse_bicep_graph(bicep_code: str) -> dict[str, Any]:
    """Parse resource nodes and explicit dependsOn edges from Bicep source text."""
    if not bicep_code.strip():
        return {
            'status': 'error',
            'message': 'No Bicep code provided.',
            'resources': [],
            'edges': [],
            'unresolvedDependencies': [],
        }

    resources = _extract_resource_blocks(bicep_code)
    if not resources:
        return {
            'status': 'error',
            'message': 'No Bicep resource declarations were found.',
            'resources': [],
            'edges': [],
            'unresolvedDependencies': [],
        }

    symbols = {resource['symbolicName'] for resource in resources}
    edges: list[dict[str, str]] = []

    for resource in resources:
        depends_on: list[str] = []
        block_text = resource['blockText']

        for dep_match in _DEPENDS_ON_RE.finditer(block_text):
            dep_text = dep_match.group('deps')
            for token in _SYMBOL_RE.findall(dep_text):
                if token == resource['symbolicName']:
                    continue
                if token not in depends_on:
                    depends_on.append(token)

        resource['dependsOn'] = depends_on
        for dependency in depends_on:
            edges.append(
                {
                    'from': dependency,
                    'to': resource['symbolicName'],
                    'kind': 'dependsOn',
                }
            )

        del resource['blockText']

    unresolved = sorted({edge['from'] for edge in edges if edge['from'] not in symbols})
    message = (
        f'Parsed {len(resources)} resources and {len(edges)} explicit dependency edges '
        f'from Bicep input.'
    )
    if unresolved:
        message += f' {len(unresolved)} dependencies did not map to local symbolic resources.'

    return {
        'status': 'success',
        'message': message,
        'resources': resources,
        'edges': edges,
        'unresolvedDependencies': unresolved,
    }


def _sanitize_identifier(name: str, used: set[str]) -> str:
    """Convert a symbolic name into a unique Python-safe identifier."""
    identifier = re.sub(r'\W+', '_', name.strip())
    if not identifier:
        identifier = 'resource'
    if identifier[0].isdigit():
        identifier = f'_{identifier}'
    if keyword.iskeyword(identifier):
        identifier = f'{identifier}_resource'

    base = identifier
    counter = 2
    while identifier in used:
        identifier = f'{base}_{counter}'
        counter += 1

    used.add(identifier)
    return identifier


def bicep_graph_to_diagram_code(graph_model: dict[str, Any]) -> str:
    """Convert a parsed Bicep graph model into runnable diagrams DSL code."""
    resources = graph_model.get('resources', [])
    edges = graph_model.get('edges', [])
    lines = ['with Diagram("Bicep Resource Graph", show=False, direction="LR"):']

    if not resources:
        lines.append('    Server("No resources found")')
        return '\n'.join(lines)

    symbol_to_var: dict[str, str] = {}
    used_identifiers: set[str] = set()

    for index, resource in enumerate(resources, start=1):
        symbolic_name = str(resource.get('symbolicName') or f'resource_{index}')
        resource_type = str(resource.get('resourceType') or 'resource')
        variable_name = _sanitize_identifier(symbolic_name, used_identifiers)
        symbol_to_var[symbolic_name] = variable_name
        label = f'{symbolic_name}\\n{resource_type}'
        lines.append(f'    {variable_name} = Server({label!r})')

    for edge in edges:
        source = symbol_to_var.get(str(edge.get('from', '')))
        target = symbol_to_var.get(str(edge.get('to', '')))
        if source and target:
            lines.append(f'    {source} >> {target}')

    return '\n'.join(lines)
