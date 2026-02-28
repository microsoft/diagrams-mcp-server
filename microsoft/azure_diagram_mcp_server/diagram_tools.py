# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Diagram generation and example functions for the Azure Diagram MCP Server."""

import base64
import diagrams
import importlib
import inspect
import logging
import mimetypes
import os
import platform
import re
import signal
import threading
import uuid
from microsoft.azure_diagram_mcp_server.models import (
    DiagramExampleResponse,
    DiagramGenerateResponse,
    DiagramIconsResponse,
    DiagramType,
)
from microsoft.azure_diagram_mcp_server.scanner import scan_python_code
from typing import Optional
from urllib.parse import unquote, urlparse


logger = logging.getLogger(__name__)

# Providers to pre-import into the execution namespace
_PROVIDERS = [
    'azure',
    'aws',
    'gcp',
    'saas',
    'onprem',
    'gis',
    'elastic',
    'programming',
    'generic',
    'k8s',
]


_SVG_HREF_RE = re.compile(r'(?P<attr>(?:xlink:)?href)\s*=\s*(?P<quote>["\'])(?P<value>.*?)(?P=quote)')


def _build_execution_namespace(output_path: str) -> dict:
    """Build a namespace with pre-imported diagram modules for code execution.

    Args:
        output_path: The output file path (without extension) for the diagram.

    Returns:
        A dictionary to be used as the execution namespace.
    """
    namespace: dict = {}

    # Core imports
    exec('import os', namespace)
    exec('import diagrams', namespace)
    exec('from diagrams import Diagram, Cluster, Edge', namespace)

    # Import all provider sub-modules
    for provider in _PROVIDERS:
        provider_module_name = f'diagrams.{provider}'
        try:
            provider_module = importlib.import_module(provider_module_name)
            for _, submodule_name, _ in __import__('pkgutil').iter_modules(
                provider_module.__path__
            ):
                full_name = f'{provider_module_name}.{submodule_name}'
                try:
                    exec(f'from {full_name} import *', namespace)
                except Exception:
                    pass
        except Exception:
            pass

    # URL retrieval for custom icons
    exec('from urllib.request import urlretrieve', namespace)

    return namespace


def _normalize_output_format(output_format: str) -> str:
    """Normalize output format to a supported value for server responses."""
    fmt = (output_format or 'png').lower().strip()
    if fmt in {'png', 'svg'}:
        return fmt
    raise ValueError('Unsupported output format. Supported values are png and svg.')


def _ensure_show_false(code: str, output_path: str, output_format: str) -> str:
    """Process diagram code to ensure show=False and set the output filename.

    Args:
        code: The original diagram code.
        output_path: The output file path (without extension) for the diagram.
        output_format: The desired output format ('png' or 'svg').

    Returns:
        The modified code with show=False and filename set.
    """
    # Ensure show=False is set in Diagram() calls
    if 'show=False' not in code:
        code = re.sub(
            r'(Diagram\([^)]*)\)',
            r'\1, show=False)',
            code,
        )

    # Set the filename in Diagram() calls
    if 'filename=' not in code:
        code = re.sub(
            r'(Diagram\([^)]*)(show=False)',
            rf'\1\2, filename="{output_path}"',
            code,
        )
    else:
        code = re.sub(
            r'filename\s*=\s*["\'][^"\']*["\']',
            f'filename="{output_path}"',
            code,
        )

    # Set/override outformat in Diagram() calls
    if 'outformat=' not in code:
        code = re.sub(
            r'(Diagram\([^)]*)\)',
            rf'\1, outformat="{output_format}")',
            code,
        )
    else:
        code = re.sub(
            r'outformat\s*=\s*(\[[^\]]*\]|["\'][^"\']*["\'])',
            f'outformat="{output_format}"',
            code,
            flags=re.S,
        )

    return code


def _resolve_svg_href_to_path(href_value: str, svg_dir: str) -> Optional[str]:
    """Resolve a local SVG href value to a filesystem path if possible."""
    value = href_value.strip()
    if not value:
        return None

    lowered = value.lower()
    if (
        lowered.startswith('data:')
        or lowered.startswith('http://')
        or lowered.startswith('https://')
        or lowered.startswith('#')
    ):
        return None

    if lowered.startswith('file://'):
        parsed = urlparse(value)
        path = unquote(parsed.path)
        return path if path else None

    return value if os.path.isabs(value) else os.path.join(svg_dir, value)


def _inline_svg_image_references(svg_path: str) -> Optional[str]:
    """Inline local image href references in an SVG as base64 data URIs."""
    try:
        with open(svg_path, encoding='utf-8') as svg_file:
            svg_text = svg_file.read()
    except OSError as exc:
        return f'Failed to read generated SVG file: {exc}'

    svg_dir = os.path.dirname(svg_path)
    changed = False

    def _replace_href(match: re.Match[str]) -> str:
        nonlocal changed
        href_value = match.group('value')
        resolved_path = _resolve_svg_href_to_path(href_value, svg_dir)
        if not resolved_path or not os.path.isfile(resolved_path):
            return match.group(0)

        try:
            with open(resolved_path, 'rb') as image_file:
                payload = base64.b64encode(image_file.read()).decode('ascii')
        except OSError:
            return match.group(0)

        mime_type, _ = mimetypes.guess_type(resolved_path)
        if not mime_type:
            mime_type = 'application/octet-stream'

        changed = True
        data_uri = f'data:{mime_type};base64,{payload}'
        quote = match.group('quote')
        return f'{match.group("attr")}={quote}{data_uri}{quote}'

    inlined_svg = _SVG_HREF_RE.sub(_replace_href, svg_text)
    if not changed:
        return None

    try:
        with open(svg_path, 'w', encoding='utf-8') as svg_file:
            svg_file.write(inlined_svg)
    except OSError as exc:
        return f'Failed to write inlined SVG file: {exc}'

    return None


async def generate_diagram(
    code: str,
    filename: Optional[str] = None,
    timeout: int = 90,
    workspace_dir: Optional[str] = None,
    output_format: str = 'png',
) -> DiagramGenerateResponse:
    """Generate a diagram from Python code using the diagrams library.

    Scans the code for security issues, sets up an execution namespace
    with pre-imported diagram modules, and executes the code with a
    platform-aware timeout.

    Args:
        code: The Python diagram code to execute.
        filename: Optional output filename (without extension).
        timeout: Timeout in seconds for diagram generation.
        workspace_dir: Optional workspace directory for output files.
        output_format: Output format for returned diagram ('png' or 'svg').

    Returns:
        A DiagramGenerateResponse with the status and file path.
    """
    # Scan code for security issues
    scan_result = await scan_python_code(code)
    if scan_result.has_errors:
        issues_text = '; '.join(issue.issue_text for issue in scan_result.security_issues)
        error_msg = scan_result.error_message or issues_text
        return DiagramGenerateResponse(
            status='error',
            message=f'Security scan failed: {error_msg}',
        )

    try:
        normalized_output_format = _normalize_output_format(output_format)
    except ValueError as exc:
        return DiagramGenerateResponse(
            status='error',
            message=str(exc),
        )

    # Generate filename if not provided
    if not filename:
        filename = f'diagram_{uuid.uuid4().hex[:8]}'

    # Remove known image extensions if present
    for ext in ('.png', '.svg'):
        if filename.endswith(ext):
            filename = filename[: -len(ext)]
            break

    # Determine output directory and path
    if os.path.isabs(filename):
        output_path = filename
        output_dir = os.path.dirname(output_path)
    else:
        base_dir = workspace_dir or os.getcwd()
        output_dir = os.path.join(base_dir, 'generated-diagrams')
        output_path = os.path.join(output_dir, filename)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Build execution namespace
    namespace = _build_execution_namespace(output_path)

    # Process code to ensure show=False and set output path
    processed_code = _ensure_show_false(code, output_path, normalized_output_format)

    # Execute with platform-aware timeout
    exec_error: Optional[str] = None

    if platform.system() != 'Windows':
        # Unix: use signal.SIGALRM
        def _timeout_handler(signum, frame):
            raise TimeoutError(f'Diagram generation timed out after {timeout} seconds')

        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)
        try:
            exec(processed_code, namespace)  # noqa: S102
        except TimeoutError as e:
            exec_error = str(e)
        except Exception as e:
            exec_error = f'Diagram generation failed: {e}'
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # Windows: use threading with daemon thread
        result_holder: dict = {}

        def _run_code():
            try:
                exec(processed_code, namespace)  # noqa: S102
            except Exception as e:
                result_holder['error'] = str(e)

        thread = threading.Thread(target=_run_code, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            exec_error = f'Diagram generation timed out after {timeout} seconds'
        elif 'error' in result_holder:
            exec_error = f'Diagram generation failed: {result_holder["error"]}'

    if exec_error:
        return DiagramGenerateResponse(
            status='error',
            message=exec_error,
        )

    # Check for generated output file
    generated_path = f'{output_path}.{normalized_output_format}'
    if not os.path.exists(generated_path):
        return DiagramGenerateResponse(
            status='error',
            message=f'Diagram file was not generated at {generated_path}',
        )

    if normalized_output_format == 'svg':
        inline_error = _inline_svg_image_references(generated_path)
        if inline_error:
            return DiagramGenerateResponse(
                status='error',
                message=inline_error,
            )

    return DiagramGenerateResponse(
        status='success',
        path=generated_path,
        message=f'Diagram generated successfully at {generated_path}',
    )


# ---------------------------------------------------------------------------
# Diagram examples
# ---------------------------------------------------------------------------

_AZURE_EXAMPLES = {
    'azure_basic': """with Diagram("Web Application Architecture", show=False):
    AppServices("App Service") >> CosmosDb("Cosmos DB")""",
    'azure_grouped_workers': """with Diagram("Scaled Worker Architecture", show=False, direction="TB"):
    ApplicationGateway("Gateway") >> [FunctionApps("worker1"),
                  FunctionApps("worker2"),
                  FunctionApps("worker3"),
                  FunctionApps("worker4"),
                  FunctionApps("worker5")] >> EventHubs("Events")""",
    'azure_clustered_web_services': """with Diagram("Clustered Web Services", show=False):
    dns = DNSZones("Azure DNS")
    lb = LoadBalancers("Load Balancer")

    with Cluster("App Services"):
        svc_group = [AppServices("web1"),
                     AppServices("web2"),
                     AppServices("web3")]

    with Cluster("Database Cluster"):
        db_primary = SQLDatabases("Primary DB")
        db_primary - [SQLDatabases("Read Replica")]

    cache = CacheForRedis("Redis Cache")

    dns >> lb >> svc_group
    svc_group >> db_primary
    svc_group >> cache""",
    'azure_event_processing': """with Diagram("Event Processing", show=False):
    source = KubernetesServices("AKS Source")

    with Cluster("Event Flows"):
        with Cluster("Event Workers"):
            workers = [ContainerInstances("worker1"),
                       ContainerInstances("worker2"),
                       ContainerInstances("worker3")]

        queue = ServiceBus("Service Bus")

        with Cluster("Processing"):
            handlers = [FunctionApps("func1"),
                        FunctionApps("func2"),
                        FunctionApps("func3")]

    store = BlobStorage("Blob Storage")
    dw = SynapseAnalytics("Synapse Analytics")

    source >> workers >> queue >> handlers
    handlers >> store
    handlers >> dw""",
    'azure_ai_services': """with Diagram("AI-Powered Image Processing", show=False, direction="LR"):
    user = User("User")

    with Cluster("Azure Storage"):
        input_blob = BlobStorage("Input Container")
        output_blob = BlobStorage("Output Container")

    function = FunctionApps("Image Processor")
    ai = CognitiveServices("Azure AI Vision")

    user >> Edge(label="Upload Image") >> input_blob
    input_blob >> Edge(label="Trigger") >> function
    function >> Edge(label="Analyze Image") >> ai
    ai >> Edge(label="Return Results") >> function
    function >> Edge(label="Save Results") >> output_blob
    output_blob >> Edge(label="Download") >> user""",
}

_SEQUENCE_EXAMPLES = {
    'sequence_basic': """with Diagram("Service Interaction", show=False, direction="LR"):
    user = User("Client")
    web = Server("Web Server")
    db = PostgreSQL("Database")

    user >> Edge(label="1. Request") >> web
    web >> Edge(label="2. Query") >> db
    db >> Edge(label="3. Result") >> web
    web >> Edge(label="4. Response") >> user""",
}

_FLOW_EXAMPLES = {
    'flow_basic': """with Diagram("Data Processing Flow", show=False, direction="LR"):
    start = User("Start")

    with Cluster("Processing"):
        step1 = Server("Validate")
        step2 = Server("Transform")
        step3 = Server("Enrich")

    store = PostgreSQL("Data Store")

    start >> step1 >> step2 >> step3 >> store""",
}

_CLASS_EXAMPLES = {
    'class_basic': """with Diagram("Service Architecture", show=False):
    with Cluster("Frontend"):
        web = Server("Web App")

    with Cluster("Backend"):
        api = Server("API Server")
        worker = Server("Worker")

    with Cluster("Data Layer"):
        db = PostgreSQL("Database")
        cache = Redis("Cache")

    web >> api
    api >> db
    api >> cache
    api >> worker
    worker >> db""",
}

_K8S_EXAMPLES = {
    'k8s_basic': """with Diagram("Kubernetes Deployment", show=False):
    ing = Ingress("Ingress")

    with Cluster("Namespace"):
        svc = Service("Service")
        pods = [Pod("pod1"), Pod("pod2"), Pod("pod3")]
        svc >> pods

    pv = PV("Persistent Volume")
    ing >> svc
    pods >> pv""",
    'k8s_stateful': """with Diagram("Stateful Application", show=False):
    ing = Ingress("Ingress")

    with Cluster("Application"):
        svc = Service("Service")
        sts = StatefulSet("StatefulSet")
        pods = [Pod("pod1"), Pod("pod2"), Pod("pod3")]

    with Cluster("Storage"):
        pvcs = [PVC("pvc1"), PVC("pvc2"), PVC("pvc3")]
        sc = StorageClass("StorageClass")

    ing >> svc >> sts
    sts >> pods
    pods >> pvcs
    pvcs >> sc""",
}

_ONPREM_EXAMPLES = {
    'onprem_basic': """with Diagram("On-Premises Architecture", show=False):
    lb = Nginx("Load Balancer")

    with Cluster("Application Servers"):
        apps = [Server("app1"),
                Server("app2"),
                Server("app3")]

    with Cluster("Database Cluster"):
        primary = PostgreSQL("Primary")
        replica = PostgreSQL("Replica")
        primary - replica

    cache = Redis("Cache")

    lb >> apps
    apps >> primary
    apps >> cache""",
}

_CUSTOM_EXAMPLES = {
    'custom_icon': """from diagrams.custom import Custom
from urllib.request import urlretrieve

rabbitmq_url = "https://jpadilla.github.io/rabbitmqapp/assets/img/icon.png"
rabbitmq_icon = "rabbitmq.png"
urlretrieve(rabbitmq_url, rabbitmq_icon)

with Diagram("Message Broker Architecture", show=False):
    producer = Server("Producer")
    consumer = Server("Consumer")
    queue = Custom("RabbitMQ", rabbitmq_icon)

    producer >> queue >> consumer""",
}


def get_diagram_examples(diagram_type: DiagramType) -> DiagramExampleResponse:
    """Return diagram examples for the requested type.

    Args:
        diagram_type: The type of diagram examples to retrieve.

    Returns:
        A DiagramExampleResponse containing a dictionary of examples.
    """
    examples: dict = {}

    type_map = {
        DiagramType.AZURE: _AZURE_EXAMPLES,
        DiagramType.SEQUENCE: _SEQUENCE_EXAMPLES,
        DiagramType.FLOW: _FLOW_EXAMPLES,
        DiagramType.CLASS: _CLASS_EXAMPLES,
        DiagramType.K8S: _K8S_EXAMPLES,
        DiagramType.ONPREM: _ONPREM_EXAMPLES,
        DiagramType.CUSTOM: _CUSTOM_EXAMPLES,
    }

    if diagram_type == DiagramType.ALL:
        for example_dict in type_map.values():
            examples.update(example_dict)
    else:
        examples.update(type_map.get(diagram_type, {}))

    return DiagramExampleResponse(examples=examples)


# ---------------------------------------------------------------------------
# Icon listing
# ---------------------------------------------------------------------------


def list_diagram_icons(
    provider_filter: Optional[str] = None,
    service_filter: Optional[str] = None,
) -> DiagramIconsResponse:
    """Dynamically inspect the diagrams package to list available icons.

    Walks through diagram provider modules to discover available node
    classes (icons) organized by provider and service.

    Args:
        provider_filter: Optional filter to narrow results by provider name.
        service_filter: Optional filter to narrow results by service name.

    Returns:
        A DiagramIconsResponse with providers, services, and icon names.
    """
    providers: dict = {}
    diagrams_path = os.path.dirname(diagrams.__file__)
    filtered = False
    filter_info: Optional[dict] = None

    # Walk through provider directories
    for provider_name in sorted(os.listdir(diagrams_path)):
        provider_dir = os.path.join(diagrams_path, provider_name)
        if not os.path.isdir(provider_dir) or provider_name.startswith('_'):
            continue

        # Apply provider filter
        if provider_filter and provider_filter.lower() not in provider_name.lower():
            continue

        services: dict = {}

        # Walk through service modules within each provider
        for service_file in sorted(os.listdir(provider_dir)):
            if not service_file.endswith('.py') or service_file.startswith('_'):
                continue

            service_name = service_file[:-3]  # Remove .py extension

            # Apply service filter
            if service_filter and service_filter.lower() not in service_name.lower():
                continue

            module_name = f'diagrams.{provider_name}.{service_name}'
            try:
                module = importlib.import_module(module_name)
                icons = [
                    name
                    for name, obj in inspect.getmembers(module, inspect.isclass)
                    if obj.__module__ == module_name and not name.startswith('_')
                ]
                if icons:
                    services[service_name] = sorted(icons)
            except Exception:
                logger.debug('Failed to import module %s', module_name)

        if services:
            providers[provider_name] = services

    if provider_filter or service_filter:
        filtered = True
        filter_info = {}
        if provider_filter:
            filter_info['provider_filter'] = provider_filter
        if service_filter:
            filter_info['service_filter'] = service_filter

    return DiagramIconsResponse(
        providers=providers,
        filtered=filtered,
        filter_info=filter_info,
    )
