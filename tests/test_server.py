# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Tests for the server module of the Azure Diagram MCP Server."""

import os
import pytest
import tempfile
from mcp.types import CallToolResult
from microsoft.azure_diagram_mcp_server.models import DiagramType
from microsoft.azure_diagram_mcp_server.server import (
    mcp_apply_edit,
    mcp_generate_diagram,
    mcp_generate_diagram_from_bicep,
    mcp_get_diagram_examples,
    mcp_list_diagram_icons,
    mcp_preview_bicep_graph,
    mcp_preview_edit,
    mcp_refresh_diagram,
    mcp_report_diagram_interaction,
    mcp_select_component,
    mcp_update_diagram_from_bicep,
)
from unittest.mock import MagicMock, patch


class TestMcpGenerateDiagram:
    """Tests for the mcp_generate_diagram tool function."""

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.generate_diagram')
    async def test_generate_diagram(self, mock_generate):
        """Verify correct args are passed and result is returned."""
        mock_result = MagicMock(
            status='success',
            path='/tmp/diagram.png',
            message='Diagram generated successfully',
        )
        mock_generate.return_value = mock_result

        with patch('microsoft.azure_diagram_mcp_server.server.os.path.exists', return_value=False):
            result = await mcp_generate_diagram(
                code='with Diagram("Test"):',
                filename='test',
                timeout=60,
                workspace_dir='/tmp',
            )

        mock_generate.assert_called_once_with('with Diagram("Test"):', 'test', 60, '/tmp', 'png')
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert result.structuredContent is not None
        assert result.structuredContent['status'] == 'success'
        assert result.structuredContent['path'] == '/tmp/diagram.png'
        assert result.structuredContent['message'] == 'Diagram generated successfully'
        assert result.structuredContent['renderFormat'] == 'png'
        assert result.structuredContent['svgData'] == ''

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.generate_diagram')
    async def test_generate_diagram_with_defaults(self, mock_generate):
        """Verify defaults are applied when only code is provided."""
        mock_result = MagicMock(
            status='success',
            path='/tmp/diagram.png',
            message='ok',
        )
        mock_generate.return_value = mock_result

        with patch('microsoft.azure_diagram_mcp_server.server.os.path.exists', return_value=False):
            result = await mcp_generate_diagram(
                code='with Diagram("Test"):', filename=None, timeout=90, workspace_dir=None
            )

        mock_generate.assert_called_once_with('with Diagram("Test"):', None, 90, None, 'png')
        assert isinstance(result, CallToolResult)
        assert result.structuredContent is not None
        assert result.structuredContent['status'] == 'success'

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.generate_diagram')
    async def test_generate_diagram_svg_payload(self, mock_generate):
        """Verify SVG payloads are returned through svgData."""
        fd, svg_path = tempfile.mkstemp(suffix='.svg')
        os.close(fd)
        try:
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write('<svg xmlns="http://www.w3.org/2000/svg"></svg>')

            mock_result = MagicMock(
                status='success',
                path=svg_path,
                message='Diagram generated successfully',
            )
            mock_generate.return_value = mock_result

            result = await mcp_generate_diagram(code='with Diagram("SVG"):', output_format='svg')

            mock_generate.assert_called_once_with('with Diagram("SVG"):', None, 90, None, 'svg')
            assert result.structuredContent is not None
            assert result.structuredContent['renderFormat'] == 'svg'
            assert result.structuredContent['svgData'].startswith('<svg')
            assert result.structuredContent['imageData'] == ''
        finally:
            if os.path.exists(svg_path):
                os.remove(svg_path)

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.generate_diagram')
    async def test_generate_diagram_error(self, mock_generate):
        """Verify error result is returned when generation fails."""
        mock_result = MagicMock(
            status='error',
            path=None,
            message='Generation failed',
        )
        mock_generate.return_value = mock_result

        result = await mcp_generate_diagram(code='with Diagram("Fail"):')

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Generation failed' in result.content[0].text


class TestMcpGetDiagramExamples:
    """Tests for the mcp_get_diagram_examples tool function."""

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.get_diagram_examples')
    async def test_get_diagram_examples(self, mock_get_examples):
        """Verify DiagramType.ALL is passed and result is returned."""
        mock_result = MagicMock(model_dump=MagicMock(return_value={'examples': {'ex1': 'code1'}}))
        mock_get_examples.return_value = mock_result

        result = await mcp_get_diagram_examples(diagram_type='all')

        mock_get_examples.assert_called_once_with(DiagramType.ALL)
        assert result == {'examples': {'ex1': 'code1'}}

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.get_diagram_examples')
    async def test_get_diagram_examples_with_specific_type(self, mock_get_examples):
        """Verify correct enum is passed for a specific type."""
        mock_result = MagicMock(
            model_dump=MagicMock(return_value={'examples': {'azure_basic': 'code'}})
        )
        mock_get_examples.return_value = mock_result

        result = await mcp_get_diagram_examples(diagram_type='azure')

        mock_get_examples.assert_called_once_with(DiagramType.AZURE)
        assert 'examples' in result


class TestMcpListDiagramIcons:
    """Tests for the mcp_list_diagram_icons tool function."""

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.list_diagram_icons')
    async def test_list_diagram_icons_without_filters(self, mock_list_icons):
        """Verify call with no filters passes None for both args."""
        mock_result = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'providers': {},
                    'filtered': False,
                    'filter_info': None,
                }
            )
        )
        mock_list_icons.return_value = mock_result

        result = await mcp_list_diagram_icons(provider_filter=None, service_filter=None)

        mock_list_icons.assert_called_once_with(None, None)
        assert result['filtered'] is False

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.list_diagram_icons')
    async def test_list_diagram_icons_with_provider_filter(self, mock_list_icons):
        """Verify provider_filter='azure' is passed as first arg."""
        mock_result = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'providers': {'azure': {}},
                    'filtered': True,
                    'filter_info': {'provider_filter': 'azure'},
                }
            )
        )
        mock_list_icons.return_value = mock_result

        result = await mcp_list_diagram_icons(provider_filter='azure', service_filter=None)

        mock_list_icons.assert_called_once_with('azure', None)
        assert result['filtered'] is True

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.list_diagram_icons')
    async def test_list_diagram_icons_with_provider_and_service_filter(self, mock_list_icons):
        """Verify both provider and service filters are passed."""
        mock_result = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'providers': {'azure': {'compute': ['VM']}},
                    'filtered': True,
                    'filter_info': {'provider_filter': 'azure', 'service_filter': 'compute'},
                }
            )
        )
        mock_list_icons.return_value = mock_result

        result = await mcp_list_diagram_icons(provider_filter='azure', service_filter='compute')

        mock_list_icons.assert_called_once_with('azure', 'compute')
        assert result['providers']['azure']['compute'] == ['VM']


class TestMcpGetDiagramExamplesStringInput:
    """Tests for string-to-DiagramType conversion in mcp_get_diagram_examples."""

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.get_diagram_examples')
    async def test_string_input_all(self, mock_get_examples):
        """Verify string 'all' converts to DiagramType.ALL."""
        mock_result = MagicMock(model_dump=MagicMock(return_value={'examples': {}}))
        mock_get_examples.return_value = mock_result

        await mcp_get_diagram_examples(diagram_type='all')

        mock_get_examples.assert_called_once_with(DiagramType.ALL)

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.get_diagram_examples')
    async def test_string_input_azure(self, mock_get_examples):
        """Verify string 'azure' converts to DiagramType.AZURE."""
        mock_result = MagicMock(model_dump=MagicMock(return_value={'examples': {}}))
        mock_get_examples.return_value = mock_result

        await mcp_get_diagram_examples(diagram_type='azure')

        mock_get_examples.assert_called_once_with(DiagramType.AZURE)

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.get_diagram_examples')
    async def test_invalid_string_falls_back_to_all(self, mock_get_examples):
        """Verify 'nonexistent' falls back to DiagramType.ALL."""
        mock_result = MagicMock(model_dump=MagicMock(return_value={'examples': {}}))
        mock_get_examples.return_value = mock_result

        await mcp_get_diagram_examples(diagram_type='nonexistent')

        mock_get_examples.assert_called_once_with(DiagramType.ALL)

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.get_diagram_examples')
    async def test_each_valid_diagram_type_string(self, mock_get_examples):
        """Verify each DiagramType value string converts correctly."""
        mock_result = MagicMock(model_dump=MagicMock(return_value={'examples': {}}))
        mock_get_examples.return_value = mock_result

        for dt in DiagramType:
            mock_get_examples.reset_mock()
            mock_get_examples.return_value = mock_result

            await mcp_get_diagram_examples(diagram_type=dt.value)

            mock_get_examples.assert_called_once_with(dt)


class TestServerIntegration:
    """Tests for server tool registration."""

    def test_server_tool_registration(self):
        """Verify MCP tool functions exist with correct docstrings."""
        assert callable(mcp_generate_diagram)
        assert mcp_generate_diagram.__doc__ is not None
        assert 'diagram' in mcp_generate_diagram.__doc__.lower()

        assert callable(mcp_get_diagram_examples)
        assert mcp_get_diagram_examples.__doc__ is not None
        assert 'example' in mcp_get_diagram_examples.__doc__.lower()

        assert callable(mcp_list_diagram_icons)
        assert mcp_list_diagram_icons.__doc__ is not None
        assert 'icon' in mcp_list_diagram_icons.__doc__.lower()

        assert callable(mcp_refresh_diagram)
        assert mcp_refresh_diagram.__doc__ is not None
        assert 'diagram' in mcp_refresh_diagram.__doc__.lower()

        assert callable(mcp_generate_diagram_from_bicep)
        assert mcp_generate_diagram_from_bicep.__doc__ is not None
        assert 'bicep' in mcp_generate_diagram_from_bicep.__doc__.lower()

        assert callable(mcp_update_diagram_from_bicep)
        assert mcp_update_diagram_from_bicep.__doc__ is not None
        assert 'bicep' in mcp_update_diagram_from_bicep.__doc__.lower()

        assert callable(mcp_select_component)
        assert mcp_select_component.__doc__ is not None
        assert 'select' in mcp_select_component.__doc__.lower()

        assert callable(mcp_preview_edit)
        assert mcp_preview_edit.__doc__ is not None
        assert 'preview' in mcp_preview_edit.__doc__.lower()

        assert callable(mcp_apply_edit)
        assert mcp_apply_edit.__doc__ is not None
        assert 'edit' in mcp_apply_edit.__doc__.lower()


class TestMcpRefreshDiagram:
    """Tests for the mcp_refresh_diagram tool function."""

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.generate_diagram')
    async def test_refresh_diagram_delegates_to_generate(self, mock_generate):
        """Verify refresh_diagram delegates to mcp_generate_diagram."""
        mock_result = MagicMock(
            status='success',
            path='/tmp/diagram.png',
            message='Diagram generated successfully',
        )
        mock_generate.return_value = mock_result

        with patch('microsoft.azure_diagram_mcp_server.server.os.path.exists', return_value=False):
            result = await mcp_refresh_diagram(
                code='with Diagram("Test"):',
                filename='test',
                timeout=60,
                workspace_dir='/tmp',
            )

        assert isinstance(result, CallToolResult)
        assert result.structuredContent is not None
        assert result.structuredContent['status'] == 'success'


class TestBicepAndInteractionTools:
    """Tests for additional MCP tools used by the viewer."""

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.parse_bicep_graph')
    async def test_preview_bicep_graph_calls_parser(self, mock_parse):
        """Verify Bicep graph preview delegates to parser."""
        mock_parse.return_value = {'status': 'success', 'resources': [], 'edges': []}

        result = await mcp_preview_bicep_graph(
            bicep_code='resource stg "Microsoft.Storage/storageAccounts@2023-05-01" = {}'
        )

        mock_parse.assert_called_once()
        assert result['status'] == 'success'

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.generate_diagram')
    @patch('microsoft.azure_diagram_mcp_server.server.bicep_graph_to_diagram_code')
    @patch('microsoft.azure_diagram_mcp_server.server.parse_bicep_graph')
    async def test_generate_diagram_from_bicep_returns_graph_model(
        self,
        mock_parse,
        mock_to_code,
        mock_generate,
    ):
        """Verify Bicep generation includes graphModel in structured content."""
        graph_model = {
            'status': 'success',
            'resources': [
                {'symbolicName': 'stg', 'resourceType': 'Microsoft.Storage/storageAccounts'}
            ],
            'edges': [],
            'unresolvedDependencies': [],
        }
        mock_parse.return_value = graph_model
        mock_to_code.return_value = (
            'with Diagram("Bicep Resource Graph", show=False):\n    stg = Server("stg")'
        )
        mock_generate.return_value = MagicMock(
            status='success',
            path='/tmp/bicep.png',
            message='Diagram generated successfully',
        )

        with patch('microsoft.azure_diagram_mcp_server.server.os.path.exists', return_value=False):
            result = await mcp_generate_diagram_from_bicep(
                bicep_code='resource stg ...',
                filename='bicep',
                timeout=60,
                workspace_dir='/tmp',
                output_format='png',
            )

        mock_parse.assert_called_once_with('resource stg ...')
        mock_to_code.assert_called_once_with(graph_model)
        mock_generate.assert_called_once_with(
            'with Diagram("Bicep Resource Graph", show=False):\n    stg = Server("stg")',
            'bicep',
            60,
            '/tmp',
            'png',
        )
        assert result.isError is False
        assert result.structuredContent is not None
        assert result.structuredContent['graphModel'] == graph_model

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.generate_diagram')
    @patch('microsoft.azure_diagram_mcp_server.server.bicep_graph_to_diagram_code')
    @patch('microsoft.azure_diagram_mcp_server.server.parse_bicep_graph')
    async def test_update_diagram_from_bicep_includes_graph_diff(
        self,
        mock_parse,
        mock_to_code,
        mock_generate,
    ):
        """Verify graphDiff is returned when previous_graph_model is supplied."""
        previous_graph = {
            'resources': [
                {'symbolicName': 'stg', 'resourceType': 'Microsoft.Storage/storageAccounts'}
            ],
            'edges': [],
        }
        current_graph = {
            'status': 'success',
            'resources': [
                {'symbolicName': 'stg', 'resourceType': 'Microsoft.Storage/storageAccounts'},
                {'symbolicName': 'vm', 'resourceType': 'Microsoft.Compute/virtualMachines'},
            ],
            'edges': [{'from': 'stg', 'to': 'vm', 'kind': 'dependsOn'}],
            'unresolvedDependencies': [],
        }
        mock_parse.return_value = current_graph
        mock_to_code.return_value = (
            'with Diagram("Bicep Resource Graph", show=False):\n    stg = Server("stg")'
        )
        mock_generate.return_value = MagicMock(
            status='success',
            path='/tmp/bicep.png',
            message='Diagram updated successfully',
        )

        with patch('microsoft.azure_diagram_mcp_server.server.os.path.exists', return_value=False):
            result = await mcp_update_diagram_from_bicep(
                bicep_code='resource stg ...',
                previous_graph_model=previous_graph,
            )

        assert result.structuredContent is not None
        graph_diff = result.structuredContent['graphDiff']
        assert graph_diff['addedResources'] == [
            {'symbolicName': 'vm', 'resourceType': 'Microsoft.Compute/virtualMachines'}
        ]
        assert graph_diff['removedResources'] == []
        assert graph_diff['addedEdges'] == [{'from': 'stg', 'to': 'vm', 'kind': 'dependsOn'}]
        assert graph_diff['removedEdges'] == []

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.server.parse_bicep_graph')
    async def test_generate_diagram_from_bicep_parse_error_returns_error(self, mock_parse):
        """Verify parser errors are surfaced as MCP tool errors."""
        mock_parse.return_value = {
            'status': 'error',
            'message': 'No Bicep code provided.',
            'resources': [],
            'edges': [],
            'unresolvedDependencies': [],
        }

        result = await mcp_generate_diagram_from_bicep(bicep_code='   ')

        assert result.isError is True
        assert result.structuredContent is not None
        assert result.structuredContent['graphModel']['status'] == 'error'

    @pytest.mark.asyncio
    async def test_report_diagram_interaction_returns_payload(self):
        """Verify app interaction reports are echoed as structured content."""
        result = await mcp_report_diagram_interaction(
            event_type='select',
            element_id='node-1',
            element_kind='node',
        )

        assert result['status'] == 'success'
        assert result['eventType'] == 'select'
        assert result['elementId'] == 'node-1'
        assert result['elementKind'] == 'node'


class TestEditIntentTools:
    """Tests for app-only edit intent tools."""

    @pytest.mark.asyncio
    async def test_select_component_returns_resource_payload(self):
        """Verify select_component resolves resource selections deterministically."""
        graph_model = {
            'status': 'success',
            'resources': [
                {'symbolicName': 'stg', 'resourceType': 'Microsoft.Storage/storageAccounts'}
            ],
            'edges': [],
        }

        result = await mcp_select_component(
            graph_model=graph_model,
            selection_intent={'componentKind': 'resource', 'symbolicName': 'stg'},
        )

        assert result['status'] == 'success'
        assert result['found'] is True
        assert result['selectedComponent'] == {'componentKind': 'resource', 'symbolicName': 'stg'}
        assert result['component']['resourceType'] == 'Microsoft.Storage/storageAccounts'

    @pytest.mark.asyncio
    async def test_preview_edit_returns_graph_diff(self):
        """Verify preview_edit returns deterministic graphDiff for add_resource intents."""
        graph_model = {
            'status': 'success',
            'resources': [
                {'symbolicName': 'stg', 'resourceType': 'Microsoft.Storage/storageAccounts'}
            ],
            'edges': [],
        }

        result = await mcp_preview_edit(
            graph_model=graph_model,
            edit_intent={
                'action': 'add_resource',
                'resource': {
                    'symbolicName': 'vm',
                    'resourceType': 'Microsoft.Compute/virtualMachines',
                },
            },
        )

        assert result['status'] == 'success'
        assert result['message'] == 'Preview generated.'
        assert result['graphDiff']['addedResources'][0]['symbolicName'] == 'vm'
        assert result['graphDiff']['addedResources'][0]['resourceType'] == (
            'Microsoft.Compute/virtualMachines'
        )
        assert result['graphDiff']['removedResources'] == []

    @pytest.mark.asyncio
    async def test_apply_edit_updates_graph_model(self):
        """Verify apply_edit returns updated graphModel and graphDiff for rename intents."""
        graph_model = {
            'status': 'success',
            'resources': [
                {'symbolicName': 'stg', 'resourceType': 'Microsoft.Storage/storageAccounts'},
                {'symbolicName': 'app', 'resourceType': 'Microsoft.Web/sites'},
            ],
            'edges': [{'from': 'stg', 'to': 'app', 'kind': 'dependsOn'}],
        }

        result = await mcp_apply_edit(
            graph_model=graph_model,
            selected_component={'componentKind': 'resource', 'symbolicName': 'stg'},
            edit_intent={'action': 'rename_resource', 'newSymbolicName': 'storage'},
        )

        assert result['status'] == 'success'
        assert result['message'] == 'Edit applied.'
        assert {'from': 'storage', 'to': 'app', 'kind': 'dependsOn'} in result['graphModel'][
            'edges'
        ]
        assert any(
            resource['symbolicName'] == 'storage' for resource in result['graphModel']['resources']
        )
        assert any(
            resource['symbolicName'] == 'stg'
            for resource in result['graphDiff']['removedResources']
        )
