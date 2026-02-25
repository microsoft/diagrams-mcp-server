# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Tests for the models module of the Azure Diagram MCP Server."""

import pytest
from microsoft.azure_diagram_mcp_server.models import (
    DiagramExampleResponse,
    DiagramGenerateRequest,
    DiagramGenerateResponse,
    DiagramIconsResponse,
    DiagramType,
)
from pydantic import ValidationError


class TestDiagramType:
    """Tests for the DiagramType enum."""

    def test_diagram_type_values(self):
        """Verify all DiagramType enum values."""
        assert DiagramType.AZURE == 'azure'
        assert DiagramType.SEQUENCE == 'sequence'
        assert DiagramType.FLOW == 'flow'
        assert DiagramType.CLASS == 'class'
        assert DiagramType.K8S == 'k8s'
        assert DiagramType.ONPREM == 'onprem'
        assert DiagramType.CUSTOM == 'custom'
        assert DiagramType.ALL == 'all'

    def test_diagram_type_from_string(self):
        """Verify DiagramType can be created from string values."""
        assert DiagramType('azure') == DiagramType.AZURE
        assert DiagramType('sequence') == DiagramType.SEQUENCE
        assert DiagramType('flow') == DiagramType.FLOW
        assert DiagramType('class') == DiagramType.CLASS
        assert DiagramType('k8s') == DiagramType.K8S
        assert DiagramType('onprem') == DiagramType.ONPREM
        assert DiagramType('custom') == DiagramType.CUSTOM
        assert DiagramType('all') == DiagramType.ALL

    def test_invalid_diagram_type(self):
        """Verify that an invalid string raises ValueError."""
        with pytest.raises(ValueError):
            DiagramType('invalid')


class TestDiagramGenerateRequest:
    """Tests for the DiagramGenerateRequest model."""

    def test_valid_request(self):
        """Verify a fully populated request is constructed correctly."""
        request = DiagramGenerateRequest(
            code='with Diagram("Test"):',
            filename='test.png',
            timeout=120,
            workspace_dir='/tmp/diagrams',
        )
        assert request.code == 'with Diagram("Test"):'
        assert request.filename == 'test.png'
        assert request.timeout == 120
        assert request.workspace_dir == '/tmp/diagrams'

    def test_minimal_request(self):
        """Verify defaults are applied when only code is provided."""
        request = DiagramGenerateRequest(code='with Diagram("Min"):')
        assert request.code == 'with Diagram("Min"):'
        assert request.filename is None
        assert request.timeout == 90
        assert request.workspace_dir is None

    def test_invalid_code(self):
        """Verify code without Diagram( raises ValidationError."""
        with pytest.raises(ValidationError, match='Diagram'):
            DiagramGenerateRequest(code='print("hello")')

    def test_invalid_timeout_zero(self):
        """Verify timeout=0 raises ValidationError."""
        with pytest.raises(ValidationError):
            DiagramGenerateRequest(code='with Diagram("T"):', timeout=0)

    def test_invalid_timeout_exceeds_max(self):
        """Verify timeout=301 raises ValidationError."""
        with pytest.raises(ValidationError):
            DiagramGenerateRequest(code='with Diagram("T"):', timeout=301)


class TestDiagramGenerateResponse:
    """Tests for the DiagramGenerateResponse model."""

    def test_success_response(self):
        """Verify a success response has the expected fields."""
        response = DiagramGenerateResponse(
            status='success',
            path='/tmp/diagram.png',
            message='Diagram generated successfully',
        )
        assert response.status == 'success'
        assert response.path == '/tmp/diagram.png'
        assert response.message == 'Diagram generated successfully'

    def test_error_response(self):
        """Verify an error response can have path=None."""
        response = DiagramGenerateResponse(
            status='error',
            path=None,
            message='Generation failed',
        )
        assert response.status == 'error'
        assert response.path is None
        assert response.message == 'Generation failed'


class TestDiagramExampleResponse:
    """Tests for the DiagramExampleResponse model."""

    def test_example_response(self):
        """Verify examples dict with multiple entries."""
        examples = {
            'azure_basic': 'with Diagram("Azure"): pass',
            'k8s_cluster': 'with Diagram("K8s"): pass',
            'flow_simple': 'with Diagram("Flow"): pass',
        }
        response = DiagramExampleResponse(examples=examples)
        assert len(response.examples) == 3
        assert 'azure_basic' in response.examples
        assert 'k8s_cluster' in response.examples
        assert 'flow_simple' in response.examples
        assert response.examples['azure_basic'] == 'with Diagram("Azure"): pass'


class TestDiagramIconsResponse:
    """Tests for the DiagramIconsResponse model."""

    def test_icons_response(self):
        """Verify nested providers dict with services and icons."""
        providers = {
            'azure': {
                'compute': ['VM', 'AppService', 'Functions'],
                'network': ['VNet', 'LoadBalancer'],
            },
            'aws': {
                'compute': ['EC2', 'Lambda'],
            },
        }
        response = DiagramIconsResponse(providers=providers)
        assert 'azure' in response.providers
        assert 'aws' in response.providers
        assert response.providers['azure']['compute'] == ['VM', 'AppService', 'Functions']
        assert response.providers['azure']['network'] == ['VNet', 'LoadBalancer']
        assert response.filtered is False
        assert response.filter_info is None
