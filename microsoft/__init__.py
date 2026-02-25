# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

# Namespace package — supports PEP 420 implicit namespace packages.
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
