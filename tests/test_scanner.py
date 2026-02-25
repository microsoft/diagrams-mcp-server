# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Tests for the scanner module of the Azure Diagram MCP Server."""

import pytest
from microsoft.azure_diagram_mcp_server.scanner import (
    check_dangerous_functions,
    check_security,
    count_code_metrics,
    scan_python_code,
    validate_syntax,
)


# ---------------------------------------------------------------------------
# TestSyntaxValidation
# ---------------------------------------------------------------------------


class TestSyntaxValidation:
    """Tests for the validate_syntax function."""

    async def test_valid_syntax(self):
        """Valid Python code should pass syntax validation."""
        is_valid, error = await validate_syntax('print("Hello")')
        assert is_valid is True
        assert error is None

    async def test_invalid_syntax(self):
        """Code with a missing closing quote should fail."""
        is_valid, error = await validate_syntax('print("Hello)')
        assert is_valid is False
        assert error is not None
        assert 'Syntax error' in error

    async def test_complex_valid_syntax(self):
        """A multi-line factorial function should pass."""
        code = (
            'def factorial(n):\n'
            '    if n <= 1:\n'
            '        return 1\n'
            '    return n * factorial(n - 1)\n'
        )
        is_valid, error = await validate_syntax(code)
        assert is_valid is True
        assert error is None

    async def test_import_rejected(self):
        """An import statement should be rejected."""
        is_valid, error = await validate_syntax('import os')
        assert is_valid is False
        assert error is not None
        assert 'Import' in error

    async def test_import_from_rejected(self):
        """A from-import statement should be rejected."""
        is_valid, error = await validate_syntax('from typing import List')
        assert is_valid is False
        assert error is not None
        assert 'Import' in error


# ---------------------------------------------------------------------------
# TestSecurityChecking
# ---------------------------------------------------------------------------


class TestSecurityChecking:
    """Tests for the check_security function."""

    async def test_safe_code(self):
        """A simple add function should have no dangerous-function issues."""
        code = 'def add(a, b):\n    return a + b\n'
        issues = await check_security(code)
        dangerous = [i for i in issues if i.issue_type == 'dangerous_function']
        assert dangerous == []

    async def test_dangerous_code(self):
        """os.system should be flagged as dangerous."""
        code = 'os.system("rm -rf /")\n'
        issues = await check_security(code)
        dangerous = [i for i in issues if i.issue_type == 'dangerous_function']
        assert len(dangerous) > 0
        texts = [i.issue_text for i in dangerous]
        assert any('os.system' in t for t in texts)

    async def test_exec_code(self):
        """exec() should be flagged as dangerous."""
        code = 'exec("print(1)")\n'
        issues = await check_security(code)
        dangerous = [i for i in issues if i.issue_type == 'dangerous_function']
        assert len(dangerous) > 0
        texts = [i.issue_text for i in dangerous]
        assert any('exec' in t for t in texts)


# ---------------------------------------------------------------------------
# TestCodeMetrics
# ---------------------------------------------------------------------------


class TestCodeMetrics:
    """Tests for the count_code_metrics function."""

    async def test_empty_code(self):
        """Empty string should yield all-zero metrics."""
        metrics = await count_code_metrics('')
        assert metrics.total_lines == 0
        assert metrics.code_lines == 0
        assert metrics.comment_lines == 0
        assert metrics.blank_lines == 0
        assert metrics.comment_ratio == 0.0

    async def test_code_with_comments(self):
        """Comments should be counted correctly."""
        code = '# comment\nx = 1\n# another comment\n'
        metrics = await count_code_metrics(code)
        assert metrics.comment_lines == 2
        assert metrics.code_lines == 1

    async def test_code_with_blank_lines(self):
        """Blank lines should be counted correctly."""
        code = 'x = 1\n\ny = 2\n\n'
        metrics = await count_code_metrics(code)
        assert metrics.blank_lines == 2
        assert metrics.code_lines == 2


# ---------------------------------------------------------------------------
# TestDangerousFunctions
# ---------------------------------------------------------------------------


class TestDangerousFunctions:
    """Tests for the check_dangerous_functions helper."""

    def test_no_dangerous_functions(self):
        """Safe code should return an empty list."""
        code = 'def add(a, b):\n    return a + b\n'
        result = check_dangerous_functions(code)
        assert result == []

    def test_exec_function(self):
        """exec() should be detected."""
        code = 'exec("print(1)")\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert 'exec' in funcs

    def test_eval_function(self):
        """eval() should be detected."""
        code = 'eval("1 + 2")\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert 'eval' in funcs

    def test_os_system(self):
        """os.system() should be detected."""
        code = 'os.system("ls")\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert 'os.system' in funcs

    def test_multiple_dangerous_functions(self):
        """Multiple dangerous calls should all be detected."""
        code = 'exec("a")\neval("b")\nos.system("c")\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert 'exec' in funcs
        assert 'eval' in funcs
        assert 'os.system' in funcs


# ---------------------------------------------------------------------------
# TestScanPythonCode
# ---------------------------------------------------------------------------


class TestScanPythonCode:
    """Tests for the scan_python_code orchestrator."""

    async def test_safe_code(self):
        """Safe code should produce no errors and be syntax-valid."""
        code = 'def add(a, b):\n    return a + b\n'
        result = await scan_python_code(code)
        assert result.syntax_valid is True
        assert result.has_errors is False

    async def test_syntax_error(self):
        """Code with a syntax error should be flagged."""
        code = 'def foo(:\n'
        result = await scan_python_code(code)
        assert result.has_errors is True
        assert result.syntax_valid is False

    async def test_security_issue(self):
        """exec/eval calls should surface as security issues."""
        code = 'exec("a")\neval("b")\n'
        result = await scan_python_code(code)
        assert result.has_errors is True
        assert result.syntax_valid is True
        funcs = [i.issue_text for i in result.security_issues]
        assert any('exec' in f for f in funcs)
        assert any('eval' in f for f in funcs)

    async def test_dangerous_function(self):
        """exec() should appear as a dangerous_function issue."""
        code = 'exec("print(1)")\n'
        result = await scan_python_code(code)
        dangerous = [i for i in result.security_issues if i.issue_type == 'dangerous_function']
        assert len(dangerous) > 0
        assert any('exec' in i.issue_text for i in dangerous)


# ---------------------------------------------------------------------------
# TestASTDangerousFunctions (comprehensive)
# ---------------------------------------------------------------------------


class TestASTDangerousFunctions:
    """Comprehensive AST-based dangerous function detection tests."""

    # -- dangerous builtins --------------------------------------------------

    @pytest.mark.parametrize(
        'builtin',
        [
            'exec',
            'eval',
            'compile',
            'getattr',
            'setattr',
            'delattr',
            'vars',
            'open',
            'globals',
            'locals',
            'breakpoint',
            '__import__',
            'spawn',
        ],
    )
    def test_dangerous_builtins(self, builtin):
        """Each dangerous builtin should be detected when called."""
        code = f'{builtin}("arg")\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert builtin in funcs

    # -- dangerous attribute calls -------------------------------------------

    @pytest.mark.parametrize(
        'attr_call',
        ['subprocess.run', 'subprocess.Popen', 'pickle.load', 'os.popen'],
    )
    def test_dangerous_attr_calls(self, attr_call):
        """Dangerous attribute-based calls should be detected."""
        code = f'{attr_call}("arg")\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert attr_call in funcs

    # -- dangerous dunders ---------------------------------------------------

    @pytest.mark.parametrize(
        'dunder',
        [
            '__dict__',
            '__builtins__',
            '__class__',
            '__subclasses__',
            '__bases__',
            '__globals__',
        ],
    )
    def test_dangerous_dunders(self, dunder):
        """Dangerous dunder attribute accesses should be detected."""
        code = f'x.{dunder}\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert dunder in funcs

    # -- false positives -----------------------------------------------------

    def test_exec_in_string_not_flagged(self):
        """The word 'exec' inside a string literal should not be flagged."""
        code = 'x = "exec is a word"\n'
        result = check_dangerous_functions(code)
        assert result == []

    def test_exec_in_comment_not_flagged(self):
        """The word 'exec' inside a comment should not be flagged."""
        code = '# exec is used here for docs\nx = 1\n'
        result = check_dangerous_functions(code)
        assert result == []

    def test_exec_in_docstring_not_flagged(self):
        """The word 'exec' inside a docstring should not be flagged."""
        code = 'def foo():\n    """Do not exec anything."""\n    pass\n'
        result = check_dangerous_functions(code)
        assert result == []

    def test_variable_executor_not_flagged(self):
        """A variable named 'executor' should not be flagged."""
        code = 'executor = 42\n'
        result = check_dangerous_functions(code)
        assert result == []

    def test_safe_diagram_code_not_flagged(self):
        """Typical diagram DSL code should not be flagged."""
        code = (
            'with Diagram("Web App", show=False):\n'
            '    web = DNS("dns")\n'
            '    web >> LB("lb") >> [EC2("w1"), EC2("w2")]\n'
        )
        result = check_dangerous_functions(code)
        assert result == []

    # -- edge cases ----------------------------------------------------------

    def test_empty_code(self):
        """Empty code should return no issues."""
        result = check_dangerous_functions('')
        assert result == []

    def test_syntax_error_fallback(self):
        """When AST parsing fails, string-based fallback should still detect issues."""
        code = 'exec("bad"\n'  # syntax error: missing closing paren
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert any('exec' in f for f in funcs)

    def test_line_number_accuracy(self):
        """Reported line numbers should match actual positions."""
        code = 'x = 1\ny = 2\nexec("z")\n'
        result = check_dangerous_functions(code)
        exec_issues = [r for r in result if r['function'] == 'exec']
        assert len(exec_issues) == 1
        assert exec_issues[0]['line'] == 3

    def test_nested_calls_both_detected(self):
        """Nested dangerous calls should both be detected."""
        code = 'exec(eval("1"))\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert 'exec' in funcs
        assert 'eval' in funcs

    # -- bypass vectors ------------------------------------------------------

    def test_getattr_bypass(self):
        """getattr() used to bypass restrictions should be detected."""
        code = 'getattr(os, "system")("ls")\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert 'getattr' in funcs

    def test_globals_bypass(self):
        """globals() used for scope manipulation should be detected."""
        code = 'globals()["__builtins__"]\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert 'globals' in funcs

    def test_vars_bypass(self):
        """vars() used for introspection should be detected."""
        code = 'vars(obj)\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert 'vars' in funcs

    def test_class_traversal(self):
        """__subclasses__() class traversal should be detected."""
        code = 'object.__subclasses__()\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert '__subclasses__' in funcs

    def test_dict_access(self):
        """__dict__ access should be detected."""
        code = 'obj.__dict__\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert '__dict__' in funcs

    def test_compile_bypass(self):
        """compile() used to create code objects should be detected."""
        code = 'compile("print(1)", "<string>", "exec")\n'
        result = check_dangerous_functions(code)
        funcs = [r['function'] for r in result]
        assert 'compile' in funcs
