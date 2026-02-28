# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Tests for the diagram tools module of the Azure Diagram MCP Server."""

import os
import pytest
import shutil
import signal
import sys
from microsoft.azure_diagram_mcp_server.diagram_tools import (
    _inline_svg_image_references,
    generate_diagram,
    get_diagram_examples,
    list_diagram_icons,
)
from microsoft.azure_diagram_mcp_server.models import DiagramType
from unittest.mock import patch


HAS_GRAPHVIZ = shutil.which('dot') is not None
requires_graphviz = pytest.mark.skipif(not HAS_GRAPHVIZ, reason='Graphviz not installed')


class TestGetDiagramExamples:
    """Tests for the get_diagram_examples function."""

    def test_get_all_examples(self):
        """ALL returns examples for every diagram type."""
        result = get_diagram_examples(DiagramType.ALL)
        keys = list(result.examples.keys())
        prefixes = ['azure_', 'sequence', 'flow', 'class', 'k8s_', 'onprem_', 'custom_']
        for prefix in prefixes:
            assert any(k.startswith(prefix) for k in keys), (
                f'Expected at least one key starting with {prefix!r}'
            )

    def test_get_azure_examples(self):
        """AZURE returns only azure_* keys."""
        result = get_diagram_examples(DiagramType.AZURE)
        assert len(result.examples) > 0
        for key in result.examples:
            assert key.startswith('azure_'), f'Expected azure_ prefix, got {key}'
        expected_keys = [
            'azure_basic',
            'azure_grouped_workers',
            'azure_clustered_web_services',
            'azure_event_processing',
            'azure_ai_services',
        ]
        for expected in expected_keys:
            assert expected in result.examples, f'Missing expected key: {expected}'

    def test_get_sequence_examples(self):
        """SEQUENCE returns sequence-related keys."""
        result = get_diagram_examples(DiagramType.SEQUENCE)
        assert len(result.examples) > 0
        assert any(k.startswith('sequence') for k in result.examples)

    def test_get_flow_examples(self):
        """FLOW returns flow-related keys."""
        result = get_diagram_examples(DiagramType.FLOW)
        assert len(result.examples) > 0
        assert any(k.startswith('flow') for k in result.examples)

    def test_get_class_examples(self):
        """CLASS returns class-related keys."""
        result = get_diagram_examples(DiagramType.CLASS)
        assert len(result.examples) > 0
        assert any(k.startswith('class') for k in result.examples)

    def test_get_k8s_examples(self):
        """K8S returns kubernetes-related keys."""
        result = get_diagram_examples(DiagramType.K8S)
        assert len(result.examples) > 0
        expected_keys = ['k8s_basic', 'k8s_stateful']
        for expected in expected_keys:
            assert expected in result.examples, f'Missing expected key: {expected}'

    def test_get_onprem_examples(self):
        """ONPREM returns on-premises-related keys."""
        result = get_diagram_examples(DiagramType.ONPREM)
        assert len(result.examples) > 0
        assert any(k.startswith('onprem') for k in result.examples)

    def test_get_custom_examples(self):
        """CUSTOM returns custom-related keys."""
        result = get_diagram_examples(DiagramType.CUSTOM)
        assert len(result.examples) > 0
        assert any(k.startswith('custom') for k in result.examples)


class TestListDiagramIcons:
    """Tests for the list_diagram_icons function."""

    def test_list_icons_without_filters(self):
        """Returns all providers when no filters are applied."""
        result = list_diagram_icons()
        assert result.filtered is False
        assert result.filter_info is None
        expected_providers = ['aws', 'gcp', 'k8s', 'onprem', 'azure', 'programming']
        for provider in expected_providers:
            assert provider in result.providers, f'Expected provider {provider!r} in results'

    def test_list_icons_with_provider_filter(self):
        """Provider filter returns only matching providers."""
        result = list_diagram_icons(provider_filter='azure')
        assert result.filtered is True
        assert 'azure' in result.providers
        azure_services = result.providers['azure']
        for service in ['compute', 'database', 'network']:
            assert service in azure_services, f'Expected service {service!r} in azure provider'

    def test_list_icons_with_provider_and_service_filter(self):
        """Provider and service filters narrow results to matching icons."""
        result = list_diagram_icons(provider_filter='azure', service_filter='compute')
        assert result.filtered is True
        assert 'azure' in result.providers
        azure_services = result.providers['azure']
        assert 'compute' in azure_services
        assert len(azure_services['compute']) > 0

    def test_list_icons_with_invalid_provider(self):
        """Invalid provider filter returns empty providers."""
        result = list_diagram_icons(provider_filter='nonexistent_provider_xyz')
        assert result.filtered is True
        assert len(result.providers) == 0
        assert result.filter_info is not None
        assert 'provider_filter' in result.filter_info

    def test_list_icons_with_invalid_service(self):
        """Invalid service filter with valid provider returns no matching services."""
        result = list_diagram_icons(
            provider_filter='azure', service_filter='nonexistent_service_xyz'
        )
        assert result.filtered is True
        assert result.filter_info is not None
        assert 'service_filter' in result.filter_info
        # No services match the filter so the provider is omitted
        assert len(result.providers) == 0 or (
            'azure' in result.providers and len(result.providers['azure']) == 0
        )

    def test_list_icons_with_service_filter_only(self):
        """Service filter without provider filters across all providers."""
        result = list_diagram_icons(service_filter='compute')
        assert result.filtered is True
        assert result.filter_info is not None
        assert 'service_filter' in result.filter_info
        # Providers that have a 'compute' service should be returned
        assert len(result.providers) > 0


class TestGenerateDiagram:
    """Tests for the generate_diagram function."""

    @requires_graphviz
    @pytest.mark.asyncio
    async def test_generate_diagram_success(self, azure_diagram_code, temp_workspace_dir):
        """Azure diagram code generates a PNG file successfully."""
        result = await generate_diagram(
            code=azure_diagram_code,
            filename='test_diagram',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'success'
        assert result.path is not None
        assert result.path.endswith('.png')
        assert os.path.exists(result.path)

    @requires_graphviz
    @pytest.mark.asyncio
    async def test_generate_diagram_with_absolute_path(
        self, azure_diagram_code, temp_workspace_dir
    ):
        """Absolute path is used correctly for diagram output."""
        abs_filename = os.path.join(temp_workspace_dir, 'abs_test_diagram')
        result = await generate_diagram(
            code=azure_diagram_code,
            filename=abs_filename,
        )
        assert result.status == 'success'
        assert result.path is not None
        assert result.path.endswith('.png')

    @requires_graphviz
    @pytest.mark.asyncio
    async def test_generate_diagram_without_filename(self, azure_diagram_code, temp_workspace_dir):
        """Random filename is generated when none is provided."""
        result = await generate_diagram(
            code=azure_diagram_code,
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'success'
        assert result.path is not None
        assert 'diagram_' in result.path

    @pytest.mark.asyncio
    async def test_generate_diagram_with_invalid_code(self, temp_workspace_dir):
        """Invalid code returns error status."""
        code = 'with Diagram("Bad", show=False):\n    raise RuntimeError("fail")'
        result = await generate_diagram(
            code=code,
            filename='invalid_test',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'

    @pytest.mark.asyncio
    async def test_generate_diagram_with_dangerous_code(
        self, dangerous_diagram_code, temp_workspace_dir
    ):
        """Dangerous code returns a security error."""
        result = await generate_diagram(
            code=dangerous_diagram_code,
            filename='dangerous_test',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'
        assert 'security' in result.message.lower()

    @requires_graphviz
    @pytest.mark.asyncio
    async def test_generate_diagram_with_timeout(self, temp_workspace_dir):
        """Short timeout causes a timeout error for slow code."""
        slow_code = (
            'with Diagram("Slow", show=False):\n    x = 0\n    while True:\n        x += 1\n'
        )
        result = await generate_diagram(
            code=slow_code,
            filename='timeout_test',
            timeout=1,
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'
        assert 'timed out' in result.message.lower() or 'failed' in result.message.lower()

    @requires_graphviz
    @pytest.mark.asyncio
    async def test_generate_sequence_diagram(self, sequence_diagram_code, temp_workspace_dir):
        """Sequence diagram code is processed without crashing."""
        result = await generate_diagram(
            code=sequence_diagram_code,
            filename='sequence_test',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status in ('success', 'error')

    @requires_graphviz
    @pytest.mark.asyncio
    async def test_generate_flow_diagram(self, flow_diagram_code, temp_workspace_dir):
        """Flow diagram code is processed without crashing."""
        result = await generate_diagram(
            code=flow_diagram_code,
            filename='flow_test',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status in ('success', 'error')

    @requires_graphviz
    @pytest.mark.asyncio
    async def test_generate_diagram_with_show_parameter(self, temp_workspace_dir):
        """Code with show=False already set works correctly."""
        code = 'with Diagram("Show Test", show=False):\n    AppServices("app") >> CosmosDb("db")\n'
        result = await generate_diagram(
            code=code,
            filename='show_test',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'success'

    @requires_graphviz
    @pytest.mark.asyncio
    async def test_generate_diagram_with_filename_parameter(self, temp_workspace_dir):
        """Code with filename= already in Diagram() is overridden."""
        code = (
            'with Diagram("Filename Test", show=False, filename="original"):\n'
            '    AppServices("app") >> CosmosDb("db")\n'
        )
        result = await generate_diagram(
            code=code,
            filename='overridden_test',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'success'
        assert result.path is not None
        assert 'overridden_test' in result.path

    @requires_graphviz
    @pytest.mark.asyncio
    async def test_generate_diagram_svg_output(self, azure_diagram_code, temp_workspace_dir):
        """Diagram generation supports SVG output format."""
        result = await generate_diagram(
            code=azure_diagram_code,
            filename='svg_test',
            workspace_dir=temp_workspace_dir,
            output_format='svg',
        )
        assert result.status == 'success'
        assert result.path is not None
        assert result.path.endswith('.svg')
        assert os.path.exists(result.path)

    @pytest.mark.asyncio
    async def test_generate_diagram_with_invalid_output_format(
        self, azure_diagram_code, temp_workspace_dir
    ):
        """Invalid output formats return an error response."""
        result = await generate_diagram(
            code=azure_diagram_code,
            filename='invalid_format',
            workspace_dir=temp_workspace_dir,
            output_format='gif',
        )
        assert result.status == 'error'
        assert 'output format' in result.message.lower()


class TestSvgInlining:
    """Tests for post-processing generated SVG files."""

    def test_inline_local_image_references(self, tmp_path):
        """Local SVG href values are replaced with base64 data URIs."""
        abs_icon = tmp_path / 'server.png'
        rel_dir = tmp_path / 'icons'
        rel_dir.mkdir()
        rel_icon = rel_dir / 'db.png'

        abs_icon.write_bytes(b'\x89PNG\r\n\x1a\n')
        rel_icon.write_bytes(b'\x89PNG\r\n\x1a\n')

        svg_path = tmp_path / 'diagram.svg'
        svg_path.write_text(
            (
                '<svg xmlns="http://www.w3.org/2000/svg">'
                f'<image xlink:href="{abs_icon}" />'
                '<image href="icons/db.png" />'
                '<image href="https://example.com/logo.png" />'
                '</svg>'
            ),
            encoding='utf-8',
        )

        error_message = _inline_svg_image_references(str(svg_path))

        assert error_message is None
        updated_svg = svg_path.read_text(encoding='utf-8')
        assert 'data:image/png;base64,' in updated_svg
        assert str(abs_icon) not in updated_svg
        assert 'icons/db.png' not in updated_svg
        assert 'https://example.com/logo.png' in updated_svg

    def test_inline_file_uri_reference(self, tmp_path):
        """file:// image href values are inlined as data URIs."""
        icon = tmp_path / 'postgres.png'
        icon.write_bytes(b'\x89PNG\r\n\x1a\n')

        svg_path = tmp_path / 'diagram.svg'
        svg_path.write_text(
            (
                '<svg xmlns="http://www.w3.org/2000/svg">'
                f'<image href="{icon.as_uri()}" />'
                '</svg>'
            ),
            encoding='utf-8',
        )

        error_message = _inline_svg_image_references(str(svg_path))

        assert error_message is None
        updated_svg = svg_path.read_text(encoding='utf-8')
        assert 'data:image/png;base64,' in updated_svg
        assert icon.as_uri() not in updated_svg


class TestCrossPlatformTimeout:
    """Tests for cross-platform timeout handling in diagram generation."""

    def test_signal_module_imported(self):
        """diagram_tools imports signal and threading modules."""
        import microsoft.azure_diagram_mcp_server.diagram_tools as dt

        assert hasattr(dt, 'signal')
        assert hasattr(dt, 'threading')

    @pytest.mark.skipif(sys.platform == 'win32', reason='Unix-only test')
    def test_unix_path_uses_sigalrm(self):
        """SIGALRM is available on Unix platforms."""
        assert hasattr(signal, 'SIGALRM')
        assert hasattr(signal, 'alarm')

    @requires_graphviz
    @pytest.mark.asyncio
    async def test_threading_fallback_when_sigalrm_unavailable(
        self, azure_diagram_code, temp_workspace_dir
    ):
        """Diagram generation works when SIGALRM is unavailable."""
        with patch('microsoft.azure_diagram_mcp_server.diagram_tools.platform') as mock_platform:
            mock_platform.system.return_value = 'Windows'
            result = await generate_diagram(
                code=azure_diagram_code,
                filename='threading_fallback_test',
                workspace_dir=temp_workspace_dir,
            )
            assert result.status == 'success'

    @pytest.mark.asyncio
    async def test_threading_timeout_triggers(self, temp_workspace_dir):
        """Threading-based timeout triggers for slow busy-loop code."""
        slow_code = (
            'with Diagram("Timeout Test", show=False):\n'
            '    x = 0\n'
            '    while True:\n'
            '        x += 1\n'
        )
        with patch('microsoft.azure_diagram_mcp_server.diagram_tools.platform') as mock_platform:
            mock_platform.system.return_value = 'Windows'
            result = await generate_diagram(
                code=slow_code,
                filename='threading_timeout_test',
                timeout=2,
                workspace_dir=temp_workspace_dir,
            )
            assert result.status == 'error'
            assert 'timed out' in result.message.lower()
