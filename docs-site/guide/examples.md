# Examples

These examples show the Python code that generates each diagram. When using the MCP server, you simply describe what you want in natural language and the AI assistant generates the code for you.

## Azure Architecture Diagram

A typical Azure web application with an Application Gateway, App Service, Functions, and Cosmos DB:

```python
from diagrams import Diagram
from diagrams.azure.compute import AppServices, FunctionApps
from diagrams.azure.database import CosmosDb
from diagrams.azure.network import ApplicationGateway

with Diagram("Azure Web Architecture", show=False):
    gateway = ApplicationGateway("Gateway")
    app = AppServices("App Service")
    functions = FunctionApps("Functions")
    db = CosmosDb("Cosmos DB")

    gateway >> app >> db
    gateway >> functions >> db
```

## Azure Microservices

A microservices architecture using AKS, Service Bus, and multiple databases:

```python
from diagrams import Cluster, Diagram
from diagrams.azure.compute import KubernetesServices
from diagrams.azure.database import CosmosDb, SqlDatabases
from diagrams.azure.integration import ServiceBus
from diagrams.azure.network import ApplicationGateway
from diagrams.azure.security import KeyVaults

with Diagram("Azure Microservices", show=False):
    gateway = ApplicationGateway("API Gateway")
    vault = KeyVaults("Key Vault")

    with Cluster("AKS Cluster"):
        svc_order = KubernetesServices("Order Service")
        svc_payment = KubernetesServices("Payment Service")
        svc_notify = KubernetesServices("Notification Service")

    bus = ServiceBus("Service Bus")
    cosmos = CosmosDb("Cosmos DB")
    sql = SqlDatabases("SQL Database")

    gateway >> svc_order
    gateway >> svc_payment
    svc_order >> bus >> svc_notify
    svc_order >> cosmos
    svc_payment >> sql
    [svc_order, svc_payment, svc_notify] >> vault
```

## Kubernetes Diagram

A Kubernetes deployment with ingress, services, and persistent storage:

```python
from diagrams import Cluster, Diagram
from diagrams.k8s.clusterconfig import HPA
from diagrams.k8s.compute import Deployment, Pod, ReplicaSet
from diagrams.k8s.network import Ingress, Service
from diagrams.k8s.storage import PV, PVC, StorageClass

with Diagram("Kubernetes Architecture", show=False):
    ingress = Ingress("ingress")

    with Cluster("Application"):
        svc = Service("service")
        hpa = HPA("autoscaler")

        with Cluster("Deployment"):
            deploy = Deployment("deployment")
            rs = ReplicaSet("replica set")
            pods = [Pod("pod-1"), Pod("pod-2"), Pod("pod-3")]

    with Cluster("Storage"):
        sc = StorageClass("storage class")
        pvc = PVC("pvc")
        pv = PV("pv")

    ingress >> svc >> pods
    hpa >> deploy >> rs >> pods
    sc >> pvc >> pv
```

## Sequence Diagram

A user authentication flow shown as a sequence diagram:

```python
from diagrams import Diagram
from diagrams.c4 import Person, System, Relationship

with Diagram("Authentication Flow", show=False, direction="TB"):
    user = Person("User")
    app = System("Web App")
    auth = System("Auth Service")
    db = System("User Database")

    user >> Relationship("1. Login request") >> app
    app >> Relationship("2. Validate credentials") >> auth
    auth >> Relationship("3. Query user") >> db
    db >> Relationship("4. User data") >> auth
    auth >> Relationship("5. JWT token") >> app
    app >> Relationship("6. Set session") >> user
```

## Custom Icon Diagram

A diagram using custom icons for specialized components:

```python
from diagrams import Cluster, Diagram
from diagrams.custom import Custom
from diagrams.azure.network import ApplicationGateway
from diagrams.azure.compute import AppServices
from diagrams.azure.database import CosmosDb

with Diagram("Custom Architecture", show=False):
    with Cluster("Frontend"):
        gateway = ApplicationGateway("API Gateway")

    with Cluster("Backend Services"):
        api = AppServices("REST API")
        worker = AppServices("Worker")

    with Cluster("Data Layer"):
        db = CosmosDb("Primary DB")
        cache = CosmosDb("Cache")

    gateway >> api >> db
    api >> cache
    gateway >> worker >> db
```

## Multi-Cloud Diagram

A hybrid architecture spanning Azure and on-premises:

```python
from diagrams import Cluster, Diagram
from diagrams.azure.compute import AppServices
from diagrams.azure.database import CosmosDb
from diagrams.azure.network import VirtualNetworks, VPNGateways
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.network import Nginx

with Diagram("Hybrid Cloud Architecture", show=False):
    with Cluster("Azure"):
        vnet = VirtualNetworks("VNet")
        app = AppServices("App Service")
        cosmos = CosmosDb("Cosmos DB")
        vpn_azure = VPNGateways("VPN Gateway")

    with Cluster("On-Premises"):
        nginx = Nginx("Load Balancer")
        pg = PostgreSQL("PostgreSQL")

    vpn_azure >> nginx
    app >> cosmos
    vnet >> vpn_azure
    nginx >> pg
    app >> vpn_azure
```

## Tips

::: tip Prompt Tips
When asking your AI assistant to generate diagrams:
- **Be specific** about the Azure services you want to use
- **Describe the data flow** between components
- **Mention grouping** if you want services clustered together
- **Specify the direction** (`LR` for left-to-right, `TB` for top-to-bottom)
:::

::: info Available Providers
Use the `list_icons` MCP tool to discover all available icons. The server supports Azure, AWS, GCP, Kubernetes, on-premises, and custom icon providers.
:::
