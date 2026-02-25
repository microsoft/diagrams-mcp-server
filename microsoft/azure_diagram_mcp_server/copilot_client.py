# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Copilot SDK client for the Azure Diagram MCP Server.

Provides a natural language interface to the diagram generation tools
by wrapping the MCP server with the GitHub Copilot SDK.
"""

import asyncio
import logging
import os
import shutil
import sys
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType
from copilot.tools import define_tool
from pydantic import BaseModel, Field
from typing import Optional


logger = logging.getLogger(__name__)

# System message that configures the LLM as a diagram architect
SYSTEM_MESSAGE = """You are an Azure Diagram Architect — an expert at creating professional \
infrastructure and architecture diagrams using the Python diagrams package DSL.

Your workflow:
1. Use `list_icons` to discover available icons and providers for diagrams.
2. Use `get_diagram_examples` to reference example code for the diagram type being created.
3. Use `generate_diagram` to submit Python code using the diagrams DSL to generate the diagram.

Guidelines:
- Always prefer Azure and Microsoft services/icons for cloud architecture diagrams.
- Use `Cluster()` to group related components logically.
- Use `Edge(label="...")` to annotate connections between components.
- Set `direction="TB"` (top-to-bottom) or `direction="LR"` (left-to-right) as appropriate.
- Always include `show=False` in `Diagram()` calls.
- Use descriptive names for all diagram nodes.
- When asked for a specific architecture, research the correct Azure service names via `list_icons` first.
- Produce clean, well-structured diagram code that follows Python best practices.

Supported diagram types: Azure architecture, sequence, flow, class, Kubernetes (K8s), \
on-premises, and custom diagrams."""

# Custom agent definition for the diagram architect persona
DIAGRAM_ARCHITECT_AGENT = {
    'name': 'azure-diagram-architect',
    'displayName': 'Azure Diagram Architect',
    'description': 'Generates professional Azure infrastructure and architecture diagrams '
    'from natural language descriptions using the Python diagrams package DSL.',
    'prompt': SYSTEM_MESSAGE,
}


def _get_mcp_server_command() -> str:
    """Get the command to start the diagram MCP server.

    Returns the appropriate command based on the environment.
    """
    if shutil.which('microsoft.azure-diagram-mcp-server'):
        return 'microsoft.azure-diagram-mcp-server'

    # Fallback to uv run
    return 'uv'


def _get_mcp_server_args() -> list[str]:
    """Get the arguments for the MCP server command."""
    if shutil.which('microsoft.azure-diagram-mcp-server'):
        return []
    return ['run', 'microsoft.azure-diagram-mcp-server']


def _build_mcp_server_config(workspace_dir: Optional[str] = None) -> dict:
    """Build the MCP server configuration for connecting to the diagram server.

    Args:
        workspace_dir: Optional working directory for the MCP server process.

    Returns:
        A dictionary with the MCP server configuration.
    """
    config: dict = {
        'type': 'local',
        'command': _get_mcp_server_command(),
        'args': _get_mcp_server_args(),
        'tools': ['*'],
    }

    if workspace_dir:
        config['cwd'] = workspace_dir

    return config


def _build_provider_config() -> Optional[dict]:
    """Build a BYOK provider configuration from environment variables.

    Supports Azure OpenAI, OpenAI, and Anthropic providers via environment
    variables. Returns None if no provider is configured (uses Copilot default).

    Environment variables:
        DIAGRAM_COPILOT_PROVIDER_TYPE: Provider type (openai, azure, anthropic)
        DIAGRAM_COPILOT_BASE_URL: API endpoint URL
        DIAGRAM_COPILOT_API_KEY: API key for the provider
        DIAGRAM_COPILOT_WIRE_API: Wire API format (completions, responses)
        DIAGRAM_COPILOT_AZURE_API_VERSION: Azure API version

    Returns:
        A provider config dict, or None if no provider env vars are set.
    """
    provider_type = os.environ.get('DIAGRAM_COPILOT_PROVIDER_TYPE')
    base_url = os.environ.get('DIAGRAM_COPILOT_BASE_URL')

    if not provider_type or not base_url:
        return None

    config: dict = {
        'type': provider_type,
        'baseUrl': base_url,
    }

    api_key = os.environ.get('DIAGRAM_COPILOT_API_KEY')
    if api_key:
        config['apiKey'] = api_key

    wire_api = os.environ.get('DIAGRAM_COPILOT_WIRE_API')
    if wire_api:
        config['wireApi'] = wire_api

    if provider_type == 'azure':
        api_version = os.environ.get('DIAGRAM_COPILOT_AZURE_API_VERSION', '2024-10-21')
        config['azure'] = {'apiVersion': api_version}

    return config


class DescribeDiagramParams(BaseModel):
    """Parameters for the describe_current_diagram tool."""

    summary: str = Field(description='Brief summary of what the diagram shows')


@define_tool(description='Provide a text description of the most recently generated diagram')
async def describe_diagram(params: DescribeDiagramParams) -> dict:
    """Return a text description of the diagram for accessibility."""
    return {'description': params.summary}


class DiagramCopilotClient:
    """High-level client for interacting with diagram tools via the Copilot SDK.

    Creates a Copilot session configured with the Azure Diagram MCP Server,
    custom agents, and system messages optimized for diagram generation.

    Example:
        >>> async with DiagramCopilotClient() as client:
        ...     response = await client.generate('Create a 3-tier Azure architecture')
        ...     print(response)
    """

    def __init__(
        self,
        model: str = 'gpt-4.1',
        streaming: bool = True,
        workspace_dir: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """Initialize the diagram copilot client.

        Args:
            model: The LLM model to use for diagram generation.
            streaming: Whether to enable streaming responses.
            workspace_dir: Optional workspace directory for diagram output.
            session_id: Optional session ID for resumable sessions.
        """
        self._model = model
        self._streaming = streaming
        self._workspace_dir = workspace_dir
        self._session_id = session_id
        self._client: Optional[CopilotClient] = None
        self._session = None
        self._event_handlers: list = []

    async def start(self) -> None:
        """Start the Copilot client and create a diagram generation session."""
        self._client = CopilotClient()
        await self._client.start()

        session_config: dict = {
            'model': self._model,
            'streaming': self._streaming,
            'systemMessage': {'content': SYSTEM_MESSAGE},
            'mcpServers': {
                'azure-diagrams': _build_mcp_server_config(self._workspace_dir),
            },
            'customAgents': [DIAGRAM_ARCHITECT_AGENT],
            'tools': [describe_diagram],
        }

        if self._session_id:
            session_config['sessionId'] = self._session_id

        provider = _build_provider_config()
        if provider:
            session_config['provider'] = provider

        self._session = await self._client.create_session(session_config)

    async def stop(self) -> None:
        """Stop the Copilot client and clean up resources."""
        if self._client:
            await self._client.stop()
            self._client = None
            self._session = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    def on_delta(self, handler) -> None:
        """Register a handler for streaming response deltas.

        Args:
            handler: Callable that receives delta content strings.
        """
        if self._session is None:
            raise RuntimeError('Client not started. Call start() first.')

        def _event_handler(event):
            if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
                handler(event.data.delta_content)

        self._session.on(_event_handler)

    def on_idle(self, handler) -> None:
        """Register a handler for when the session becomes idle.

        Args:
            handler: Callable invoked when the session is idle.
        """
        if self._session is None:
            raise RuntimeError('Client not started. Call start() first.')

        def _event_handler(event):
            if event.type == SessionEventType.SESSION_IDLE:
                handler()

        self._session.on(_event_handler)

    async def generate(self, prompt: str) -> Optional[str]:
        """Send a diagram generation prompt and return the response.

        Args:
            prompt: Natural language description of the desired diagram.

        Returns:
            The assistant's response content, or None if no response.

        Raises:
            RuntimeError: If the client has not been started.
        """
        if self._session is None:
            raise RuntimeError('Client not started. Call start() first.')

        response = await self._session.send_and_wait({'prompt': prompt})
        if response and response.data and response.data.content:
            return response.data.content
        return None

    async def resume(self, session_id: str) -> None:
        """Resume a previously saved session.

        Args:
            session_id: The session ID to resume.

        Raises:
            RuntimeError: If the client has not been started.
        """
        if self._client is None:
            raise RuntimeError('Client not started. Call start() first.')

        self._session = await self._client.resume_session(session_id)


async def _run_interactive() -> None:
    """Run the diagram copilot in interactive mode."""
    model = os.environ.get('DIAGRAM_COPILOT_MODEL', 'gpt-4.1')
    workspace_dir = os.environ.get('DIAGRAM_COPILOT_WORKSPACE_DIR')

    print('Azure Diagram Copilot')
    print('=' * 40)
    print(f'Model: {model}')
    print('Type your diagram request, or "quit" to exit.')
    print()

    async with DiagramCopilotClient(
        model=model,
        streaming=True,
        workspace_dir=workspace_dir,
    ) as client:
        # Set up streaming output
        client.on_delta(lambda delta: sys.stdout.write(delta) or sys.stdout.flush())
        client.on_idle(lambda: print())

        while True:
            try:
                prompt = input('\n> ').strip()
            except (EOFError, KeyboardInterrupt):
                print('\nGoodbye!')
                break

            if not prompt:
                continue
            if prompt.lower() in ('quit', 'exit', 'q'):
                print('Goodbye!')
                break

            await client.generate(prompt)


def main():
    """CLI entry point for the diagram copilot."""
    asyncio.run(_run_interactive())


if __name__ == '__main__':
    main()
