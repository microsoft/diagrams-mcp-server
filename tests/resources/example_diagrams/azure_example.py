# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Example Azure architecture diagram for testing."""

from diagrams import Diagram
from diagrams.azure.compute import AppServices, FunctionApps
from diagrams.azure.database import CosmosDb
from diagrams.azure.network import ApplicationGateway


with Diagram('Azure Web Architecture', show=False):
    gateway = ApplicationGateway('Gateway')
    app = AppServices('App Service')
    functions = FunctionApps('Functions')
    db = CosmosDb('Cosmos DB')

    gateway >> app >> db
    gateway >> functions >> db
