# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Tests for Bicep parsing and diagram code generation helpers."""

from microsoft.azure_diagram_mcp_server.bicep_tools import (
    bicep_graph_to_diagram_code,
    parse_bicep_graph,
)


class TestParseBicepGraph:
    """Tests for parse_bicep_graph."""

    def test_parse_simple_resource(self):
        """Single Bicep resource is extracted into resource list."""
        code = """
resource stg 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stgacct'
  location: resourceGroup().location
}
"""
        result = parse_bicep_graph(code)

        assert result['status'] == 'success'
        assert len(result['resources']) == 1
        resource = result['resources'][0]
        assert resource['symbolicName'] == 'stg'
        assert resource['resourceType'] == 'Microsoft.Storage/storageAccounts'

    def test_parse_explicit_depends_on(self):
        """Explicit dependsOn entries produce directed edges."""
        code = """
resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: 'vnet-main'
}

resource vm 'Microsoft.Compute/virtualMachines@2023-09-01' = {
  name: 'vm-main'
  dependsOn: [
    vnet
  ]
}
"""
        result = parse_bicep_graph(code)

        assert result['status'] == 'success'
        assert {'from': 'vnet', 'to': 'vm', 'kind': 'dependsOn'} in result['edges']
        assert result['unresolvedDependencies'] == []

    def test_empty_bicep_input(self):
        """Empty Bicep source returns a validation error."""
        result = parse_bicep_graph('   ')

        assert result['status'] == 'error'
        assert 'no bicep code' in result['message'].lower()


class TestBicepGraphToDiagramCode:
    """Tests for bicep_graph_to_diagram_code."""

    def test_generates_scanner_safe_diagram_code(self):
        """Generated code should contain Diagram DSL without import statements."""
        graph_model = {
            'resources': [
                {
                    'symbolicName': 'stg',
                    'resourceType': 'Microsoft.Storage/storageAccounts',
                }
            ],
            'edges': [],
        }

        code = bicep_graph_to_diagram_code(graph_model)

        assert 'with Diagram("Bicep Resource Graph"' in code
        assert "stg = Server('stg\\\\nMicrosoft.Storage/storageAccounts')" in code
        assert 'import ' not in code

    def test_generates_edges_from_graph_dependencies(self):
        """Dependency edges should be translated into diagrams edge statements."""
        code = """
resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: 'vnet-main'
}

resource vm 'Microsoft.Compute/virtualMachines@2023-09-01' = {
  name: 'vm-main'
  dependsOn: [
    vnet
  ]
}
"""
        graph_model = parse_bicep_graph(code)

        diagram_code = bicep_graph_to_diagram_code(graph_model)

        assert 'vnet = Server(' in diagram_code
        assert 'vm = Server(' in diagram_code
        assert 'vnet >> vm' in diagram_code
