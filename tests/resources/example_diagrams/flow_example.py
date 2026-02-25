# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Example flow diagram for testing."""

from diagrams import Diagram
from diagrams.programming.flowchart import Action, Decision, Predefined


with Diagram('Order Processing Flow', show=False):
    start = Predefined('Start')
    process = Action('Process Order')
    check = Decision('Valid?')

    start >> check >> process
