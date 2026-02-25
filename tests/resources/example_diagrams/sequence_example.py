# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Example sequence diagram for testing."""

from diagrams import Diagram
from diagrams.programming.flowchart import Action, Decision, InputOutput


with Diagram('User Authentication', show=False):
    login = InputOutput('Login')
    auth = Decision('Auth?')
    granted = Action('Granted')

    login >> auth >> granted
