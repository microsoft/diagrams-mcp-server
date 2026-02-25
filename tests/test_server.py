# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Tests for the server module of the Azure Diagram MCP Server."""

import pytest
from mcp.types import CallToolResult
from microsoft.azure_diagram_mcp_server.models import DiagramType
from microsoft.azure_diagram_mcp_server.server import (
    mcp_generate_diagram,
    mcp_get_diagram_examples,
    mcp_list_diagram_icons,
    mcp_refresh_diagram,
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

        mock_generate.assert_called_once_with('with Diagram("Test"):', 'test', 60, '/tmp')
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert result.structuredContent['status'] == 'success'
        assert result.structuredContent['path'] == '/tmp/diagram.png'
        assert result.structuredContent['message'] == 'Diagram generated successfully'

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

        mock_generate.assert_called_once_with('with Diagram("Test"):', None, 90, None)
        assert isinstance(result, CallToolResult)
        assert result.structuredContent['status'] == 'success'

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
        assert 'diagram' in mcp_generate_diagram.__doc__.lower()

        assert callable(mcp_get_diagram_examples)
        assert 'example' in mcp_get_diagram_examples.__doc__.lower()

        assert callable(mcp_list_diagram_icons)
        assert 'icon' in mcp_list_diagram_icons.__doc__.lower()

        assert callable(mcp_refresh_diagram)
        assert 'diagram' in mcp_refresh_diagram.__doc__.lower()


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
        assert result.structuredContent['status'] == 'success'
