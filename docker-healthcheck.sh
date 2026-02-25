#!/bin/sh
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

SERVER="azure-diagram-mcp-server"

# Check if the server process is running
if pgrep -f "microsoft.$SERVER" > /dev/null; then
  echo -n "$SERVER is running";
  exit 0;
fi;

# Unhealthy
exit 1;
