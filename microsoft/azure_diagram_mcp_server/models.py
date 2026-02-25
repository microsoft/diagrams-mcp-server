# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Models for the Azure Diagram MCP Server."""

from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Literal, Optional


class DiagramType(str, Enum):
    """Supported diagram types for the Azure Diagram MCP Server.

    Attributes:
        AZURE: Azure cloud architecture diagrams.
        SEQUENCE: Sequence diagrams.
        FLOW: Flow diagrams.
        CLASS: Class diagrams.
        K8S: Kubernetes diagrams.
        ONPREM: On-premises infrastructure diagrams.
        CUSTOM: Custom diagrams.
        ALL: All diagram types.
    """

    AZURE = 'azure'
    SEQUENCE = 'sequence'
    FLOW = 'flow'
    CLASS = 'class'
    K8S = 'k8s'
    ONPREM = 'onprem'
    CUSTOM = 'custom'
    ALL = 'all'


class DiagramGenerateRequest(BaseModel):
    """Request model for generating a diagram.

    Attributes:
        code: The diagram code to render. Must contain a 'Diagram(' call.
        filename: Optional output filename for the generated diagram.
        timeout: Timeout in seconds for diagram generation.
        workspace_dir: Optional workspace directory for output files.
    """

    code: str = Field(
        ...,
        description='The diagram code to render. Must contain a Diagram() call.',
    )
    filename: Optional[str] = Field(
        default=None,
        description='Optional output filename for the generated diagram.',
    )
    timeout: int = Field(
        default=90,
        ge=1,
        le=300,
        description='Timeout in seconds for diagram generation.',
    )
    workspace_dir: Optional[str] = Field(
        default=None,
        description='Optional workspace directory for output files.',
    )

    @field_validator('code')
    @classmethod
    def validate_code_contains_diagram(cls, v: str) -> str:
        """Validate that the code contains a Diagram() call."""
        if 'Diagram(' not in v:
            raise ValueError(
                'Code must contain a Diagram() call. Example: with Diagram("My Diagram"):'
            )
        return v


class DiagramExampleRequest(BaseModel):
    """Request model for retrieving diagram examples.

    Attributes:
        diagram_type: The type of diagram examples to retrieve.
    """

    diagram_type: DiagramType = Field(
        default=DiagramType.ALL,
        description='The type of diagram examples to retrieve.',
    )


class DiagramGenerateResponse(BaseModel):
    """Response model for diagram generation.

    Attributes:
        status: The status of the diagram generation.
        path: The file path of the generated diagram.
        message: A message describing the result.
    """

    status: Literal['success', 'error']
    path: Optional[str] = None
    message: str


class DiagramExampleResponse(BaseModel):
    """Response model for diagram examples.

    Attributes:
        examples: A dictionary mapping example names to their code.
    """

    examples: Dict[str, str]


class DiagramIconsRequest(BaseModel):
    """Request model for retrieving available diagram icons.

    Attributes:
        provider_filter: Optional filter to narrow results by provider name.
        service_filter: Optional filter to narrow results by service name.
    """

    provider_filter: Optional[str] = Field(
        default=None,
        description='Optional filter to narrow results by provider name.',
    )
    service_filter: Optional[str] = Field(
        default=None,
        description='Optional filter to narrow results by service name.',
    )


class DiagramIconsResponse(BaseModel):
    """Response model for available diagram icons.

    Attributes:
        providers: Nested dictionary of providers, services, and icon names.
        filtered: Whether the results have been filtered.
        filter_info: Optional metadata about applied filters.
    """

    providers: Dict[str, Dict[str, List[str]]]
    filtered: bool = False
    filter_info: Optional[Dict[str, str]] = None
