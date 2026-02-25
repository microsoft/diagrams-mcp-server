# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Tests for the Copilot SDK client module of the Azure Diagram MCP Server."""

import os
import pytest
from microsoft.azure_diagram_mcp_server.copilot_client import (
    DIAGRAM_ARCHITECT_AGENT,
    SYSTEM_MESSAGE,
    DiagramCopilotClient,
    _build_mcp_server_config,
    _build_provider_config,
    _get_mcp_server_args,
    _get_mcp_server_command,
    describe_diagram,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestSystemMessage:
    """Tests for the system message configuration."""

    def test_system_message_contains_workflow(self):
        """Verify system message describes the diagram workflow."""
        assert 'list_icons' in SYSTEM_MESSAGE
        assert 'get_diagram_examples' in SYSTEM_MESSAGE
        assert 'generate_diagram' in SYSTEM_MESSAGE

    def test_system_message_mentions_azure(self):
        """Verify system message emphasizes Azure support."""
        assert 'Azure' in SYSTEM_MESSAGE

    def test_system_message_mentions_show_false(self):
        """Verify system message instructs to use show=False."""
        assert 'show=False' in SYSTEM_MESSAGE


class TestDiagramArchitectAgent:
    """Tests for the custom agent configuration."""

    def test_agent_has_required_fields(self):
        """Verify the agent config has all required fields."""
        assert 'name' in DIAGRAM_ARCHITECT_AGENT
        assert 'displayName' in DIAGRAM_ARCHITECT_AGENT
        assert 'description' in DIAGRAM_ARCHITECT_AGENT
        assert 'prompt' in DIAGRAM_ARCHITECT_AGENT

    def test_agent_name(self):
        """Verify the agent name is correct."""
        assert DIAGRAM_ARCHITECT_AGENT['name'] == 'azure-diagram-architect'

    def test_agent_prompt_matches_system_message(self):
        """Verify the agent prompt uses the system message."""
        assert DIAGRAM_ARCHITECT_AGENT['prompt'] == SYSTEM_MESSAGE


class TestMcpServerConfig:
    """Tests for MCP server configuration helpers."""

    @patch('microsoft.azure_diagram_mcp_server.copilot_client.shutil')
    def test_get_mcp_server_command_installed(self, mock_shutil):
        """Verify command returns binary name when installed."""
        mock_shutil.which.return_value = '/usr/local/bin/microsoft.azure-diagram-mcp-server'
        assert _get_mcp_server_command() == 'microsoft.azure-diagram-mcp-server'

    @patch('microsoft.azure_diagram_mcp_server.copilot_client.shutil')
    def test_get_mcp_server_command_fallback(self, mock_shutil):
        """Verify command falls back to uv when not installed."""
        mock_shutil.which.return_value = None
        assert _get_mcp_server_command() == 'uv'

    @patch('microsoft.azure_diagram_mcp_server.copilot_client.shutil')
    def test_get_mcp_server_args_installed(self, mock_shutil):
        """Verify empty args when binary is installed."""
        mock_shutil.which.return_value = '/usr/local/bin/microsoft.azure-diagram-mcp-server'
        assert _get_mcp_server_args() == []

    @patch('microsoft.azure_diagram_mcp_server.copilot_client.shutil')
    def test_get_mcp_server_args_fallback(self, mock_shutil):
        """Verify uv run args when falling back."""
        mock_shutil.which.return_value = None
        assert _get_mcp_server_args() == ['run', 'microsoft.azure-diagram-mcp-server']

    def test_build_mcp_server_config_basic(self):
        """Verify basic MCP server config structure."""
        config = _build_mcp_server_config()
        assert config['type'] == 'local'
        assert 'command' in config
        assert 'args' in config
        assert config['tools'] == ['*']

    def test_build_mcp_server_config_with_workspace(self):
        """Verify workspace_dir is set as cwd."""
        config = _build_mcp_server_config(workspace_dir='/tmp/diagrams')
        assert config['cwd'] == '/tmp/diagrams'

    def test_build_mcp_server_config_without_workspace(self):
        """Verify no cwd when workspace_dir is None."""
        config = _build_mcp_server_config()
        assert 'cwd' not in config


class TestProviderConfig:
    """Tests for BYOK provider configuration."""

    def test_no_provider_when_env_not_set(self):
        """Verify None returned when no provider env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            assert _build_provider_config() is None

    def test_no_provider_when_partial_env(self):
        """Verify None returned when only type is set."""
        with patch.dict(os.environ, {'DIAGRAM_COPILOT_PROVIDER_TYPE': 'openai'}, clear=True):
            assert _build_provider_config() is None

    def test_openai_provider(self):
        """Verify OpenAI provider config from env vars."""
        env = {
            'DIAGRAM_COPILOT_PROVIDER_TYPE': 'openai',
            'DIAGRAM_COPILOT_BASE_URL': 'https://api.openai.com/v1',
            'DIAGRAM_COPILOT_API_KEY': 'sk-test-key',
        }
        with patch.dict(os.environ, env, clear=True):
            config = _build_provider_config()
            assert config is not None
            assert config['type'] == 'openai'
            assert config['baseUrl'] == 'https://api.openai.com/v1'
            assert config['apiKey'] == 'sk-test-key'

    def test_azure_provider(self):
        """Verify Azure provider config includes apiVersion."""
        env = {
            'DIAGRAM_COPILOT_PROVIDER_TYPE': 'azure',
            'DIAGRAM_COPILOT_BASE_URL': 'https://my-resource.openai.azure.com',
            'DIAGRAM_COPILOT_API_KEY': 'azure-key',
        }
        with patch.dict(os.environ, env, clear=True):
            config = _build_provider_config()
            assert config is not None
            assert config['type'] == 'azure'
            assert 'azure' in config
            assert config['azure']['apiVersion'] == '2024-10-21'

    def test_azure_provider_custom_api_version(self):
        """Verify custom Azure API version from env."""
        env = {
            'DIAGRAM_COPILOT_PROVIDER_TYPE': 'azure',
            'DIAGRAM_COPILOT_BASE_URL': 'https://my-resource.openai.azure.com',
            'DIAGRAM_COPILOT_AZURE_API_VERSION': '2025-01-01',
        }
        with patch.dict(os.environ, env, clear=True):
            config = _build_provider_config()
            assert config is not None
            assert config['azure']['apiVersion'] == '2025-01-01'

    def test_wire_api_config(self):
        """Verify wireApi is set from env."""
        env = {
            'DIAGRAM_COPILOT_PROVIDER_TYPE': 'openai',
            'DIAGRAM_COPILOT_BASE_URL': 'https://api.example.com/v1',
            'DIAGRAM_COPILOT_WIRE_API': 'responses',
        }
        with patch.dict(os.environ, env, clear=True):
            config = _build_provider_config()
            assert config is not None
            assert config['wireApi'] == 'responses'


class TestDescribeDiagramTool:
    """Tests for the describe_diagram custom tool."""

    def test_describe_diagram_is_tool(self):
        """Verify describe_diagram is wrapped as a Tool by @define_tool."""
        assert describe_diagram is not None
        assert hasattr(describe_diagram, 'name') or hasattr(describe_diagram, 'description')


class TestDiagramCopilotClient:
    """Tests for the DiagramCopilotClient class."""

    def test_init_defaults(self):
        """Verify default initialization parameters."""
        client = DiagramCopilotClient()
        assert client._model == 'gpt-4.1'
        assert client._streaming is True
        assert client._workspace_dir is None
        assert client._session_id is None
        assert client._client is None
        assert client._session is None

    def test_init_custom_params(self):
        """Verify custom initialization parameters."""
        client = DiagramCopilotClient(
            model='claude-sonnet-4',
            streaming=False,
            workspace_dir='/tmp/diagrams',
            session_id='test-session-123',
        )
        assert client._model == 'claude-sonnet-4'
        assert client._streaming is False
        assert client._workspace_dir == '/tmp/diagrams'
        assert client._session_id == 'test-session-123'

    @pytest.mark.asyncio
    async def test_generate_raises_when_not_started(self):
        """Verify generate raises RuntimeError when client not started."""
        client = DiagramCopilotClient()
        with pytest.raises(RuntimeError, match='Client not started'):
            await client.generate('Create a diagram')

    def test_on_delta_raises_when_not_started(self):
        """Verify on_delta raises RuntimeError when client not started."""
        client = DiagramCopilotClient()
        with pytest.raises(RuntimeError, match='Client not started'):
            client.on_delta(lambda x: None)

    def test_on_idle_raises_when_not_started(self):
        """Verify on_idle raises RuntimeError when client not started."""
        client = DiagramCopilotClient()
        with pytest.raises(RuntimeError, match='Client not started'):
            client.on_idle(lambda: None)

    @pytest.mark.asyncio
    async def test_resume_raises_when_not_started(self):
        """Verify resume raises RuntimeError when client not started."""
        client = DiagramCopilotClient()
        with pytest.raises(RuntimeError, match='Client not started'):
            await client.resume('some-session-id')

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.copilot_client.CopilotClient')
    async def test_start_creates_session(self, MockCopilotClient):
        """Verify start() creates a CopilotClient and session."""
        mock_client = AsyncMock()
        mock_session = AsyncMock()
        mock_client.create_session.return_value = mock_session
        MockCopilotClient.return_value = mock_client

        client = DiagramCopilotClient()
        await client.start()

        mock_client.start.assert_awaited_once()
        mock_client.create_session.assert_awaited_once()

        # Verify session config
        session_config = mock_client.create_session.call_args[0][0]
        assert session_config['model'] == 'gpt-4.1'
        assert session_config['streaming'] is True
        assert 'systemMessage' in session_config
        assert 'azure-diagrams' in session_config['mcpServers']
        assert len(session_config['customAgents']) == 1
        assert session_config['customAgents'][0]['name'] == 'azure-diagram-architect'

        await client.stop()

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.copilot_client.CopilotClient')
    async def test_start_with_session_id(self, MockCopilotClient):
        """Verify session ID is included in config when provided."""
        mock_client = AsyncMock()
        mock_session = AsyncMock()
        mock_client.create_session.return_value = mock_session
        MockCopilotClient.return_value = mock_client

        client = DiagramCopilotClient(session_id='my-session-42')
        await client.start()

        session_config = mock_client.create_session.call_args[0][0]
        assert session_config['sessionId'] == 'my-session-42'

        await client.stop()

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.copilot_client._build_provider_config')
    @patch('microsoft.azure_diagram_mcp_server.copilot_client.CopilotClient')
    async def test_start_with_byok_provider(self, MockCopilotClient, mock_provider):
        """Verify BYOK provider config is included when set."""
        mock_client = AsyncMock()
        mock_session = AsyncMock()
        mock_client.create_session.return_value = mock_session
        MockCopilotClient.return_value = mock_client

        mock_provider.return_value = {
            'type': 'openai',
            'baseUrl': 'https://api.openai.com/v1',
            'apiKey': 'sk-test',
        }

        client = DiagramCopilotClient()
        await client.start()

        session_config = mock_client.create_session.call_args[0][0]
        assert 'provider' in session_config
        assert session_config['provider']['type'] == 'openai'

        await client.stop()

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.copilot_client.CopilotClient')
    async def test_stop_cleans_up(self, MockCopilotClient):
        """Verify stop() cleans up client and session."""
        mock_client = AsyncMock()
        mock_session = AsyncMock()
        mock_client.create_session.return_value = mock_session
        MockCopilotClient.return_value = mock_client

        client = DiagramCopilotClient()
        await client.start()
        await client.stop()

        mock_client.stop.assert_awaited_once()
        assert client._client is None
        assert client._session is None

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.copilot_client.CopilotClient')
    async def test_context_manager(self, MockCopilotClient):
        """Verify async context manager starts and stops client."""
        mock_client = AsyncMock()
        mock_session = AsyncMock()
        mock_client.create_session.return_value = mock_session
        MockCopilotClient.return_value = mock_client

        async with DiagramCopilotClient() as client:
            assert client._session is not None

        mock_client.start.assert_awaited_once()
        mock_client.stop.assert_awaited_once()

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.copilot_client.CopilotClient')
    async def test_generate_sends_prompt(self, MockCopilotClient):
        """Verify generate() sends prompt and returns content."""
        mock_client = AsyncMock()
        mock_session = AsyncMock()
        mock_response = MagicMock()
        mock_response.data.content = 'Diagram generated successfully at /tmp/diagram.png'
        mock_session.send_and_wait.return_value = mock_response
        mock_client.create_session.return_value = mock_session
        MockCopilotClient.return_value = mock_client

        async with DiagramCopilotClient() as client:
            result = await client.generate('Create an Azure web app diagram')

        mock_session.send_and_wait.assert_awaited_once_with(
            {'prompt': 'Create an Azure web app diagram'}
        )
        assert result == 'Diagram generated successfully at /tmp/diagram.png'

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.copilot_client.CopilotClient')
    async def test_generate_returns_none_for_empty_response(self, MockCopilotClient):
        """Verify generate() returns None when response has no content."""
        mock_client = AsyncMock()
        mock_session = AsyncMock()
        mock_session.send_and_wait.return_value = None
        mock_client.create_session.return_value = mock_session
        MockCopilotClient.return_value = mock_client

        async with DiagramCopilotClient() as client:
            result = await client.generate('Create something')

        assert result is None

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.copilot_client.CopilotClient')
    async def test_resume_session(self, MockCopilotClient):
        """Verify resume() calls client.resume_session."""
        mock_client = AsyncMock()
        mock_session = AsyncMock()
        mock_resumed = AsyncMock()
        mock_client.create_session.return_value = mock_session
        mock_client.resume_session.return_value = mock_resumed
        MockCopilotClient.return_value = mock_client

        client = DiagramCopilotClient()
        await client.start()
        await client.resume('session-to-resume')

        mock_client.resume_session.assert_awaited_once_with('session-to-resume')
        assert client._session == mock_resumed

        await client.stop()

    @pytest.mark.asyncio
    @patch('microsoft.azure_diagram_mcp_server.copilot_client.CopilotClient')
    async def test_on_delta_registers_handler(self, MockCopilotClient):
        """Verify on_delta registers an event handler on the session."""
        mock_client = AsyncMock()
        mock_session = MagicMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)
        mock_client.start = AsyncMock()
        mock_client.stop = AsyncMock()
        MockCopilotClient.return_value = mock_client

        client = DiagramCopilotClient()
        await client.start()
        client.on_delta(lambda x: None)

        mock_session.on.assert_called_once()

        await client.stop()


class TestMcpServerConfigIntegration:
    """Integration-style tests for MCP server config with workspace dirs."""

    def test_mcp_config_tools_wildcard(self):
        """Verify tools is set to wildcard for all tools."""
        config = _build_mcp_server_config()
        assert config['tools'] == ['*']

    def test_mcp_config_type_is_local(self):
        """Verify MCP server type is local."""
        config = _build_mcp_server_config()
        assert config['type'] == 'local'
