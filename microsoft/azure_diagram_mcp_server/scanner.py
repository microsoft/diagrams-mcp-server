# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Security scanner for the Azure Diagram MCP Server."""

import ast
import os
import tempfile
import warnings
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Tuple


# Suppress AST deprecation warnings
warnings.filterwarnings('ignore', category=DeprecationWarning, module='ast')


class SecurityIssue(BaseModel):
    """Represents a security issue found during code scanning.

    Attributes:
        severity: The severity level of the issue (e.g., HIGH, MEDIUM, LOW).
        confidence: The confidence level of the detection.
        line: The line number where the issue was found.
        issue_text: A description of the security issue.
        issue_type: The category or type of the issue.
    """

    severity: str
    confidence: str
    line: int
    issue_text: str
    issue_type: str


class CodeMetrics(BaseModel):
    """Metrics about the scanned code.

    Attributes:
        total_lines: Total number of lines in the code.
        code_lines: Number of lines containing code.
        comment_lines: Number of lines that are comments.
        blank_lines: Number of blank lines.
        comment_ratio: Percentage of comment lines relative to total lines.
    """

    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    comment_ratio: float


class CodeScanResult(BaseModel):
    """Result of a complete code scan.

    Attributes:
        has_errors: Whether any errors were found during scanning.
        syntax_valid: Whether the code has valid Python syntax.
        security_issues: List of security issues found.
        error_message: Optional error message if scanning failed.
        metrics: Optional code metrics.
    """

    has_errors: bool
    syntax_valid: bool
    security_issues: List[SecurityIssue]
    error_message: Optional[str] = None
    metrics: Optional[CodeMetrics] = None


# Dangerous built-in functions that should not be allowed in user code
DANGEROUS_BUILTINS = {
    'exec',
    'eval',
    'compile',
    'getattr',
    'setattr',
    'delattr',
    'vars',
    '__import__',
    'breakpoint',
    'open',
    'globals',
    'locals',
    'spawn',
}

# Dangerous attribute-based calls (module.function patterns)
DANGEROUS_ATTR_CALLS = {
    'os.system',
    'os.popen',
    'pickle.loads',
    'pickle.load',
}

# Dangerous dunder attributes
DANGEROUS_DUNDERS = {
    '__dict__',
    '__builtins__',
    '__class__',
    '__subclasses__',
    '__bases__',
    '__globals__',
    '__mro__',
}


def _get_attribute_name(node: ast.AST) -> Optional[str]:
    """Build a dotted name from an AST Attribute or Name node.

    Args:
        node: An AST node to extract the attribute name from.

    Returns:
        The dotted attribute name string, or None if the node type
        is not supported.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _get_attribute_name(node.value)
        if parent is not None:
            return f'{parent}.{node.attr}'
    return None


def check_dangerous_functions(code: str) -> List[Dict[str, Any]]:
    """Detect dangerous function calls and attribute accesses in code.

    Uses AST-based analysis to find calls to dangerous built-in functions,
    dangerous module-level calls, subprocess usage, and dangerous dunder
    attribute accesses. Falls back to string-based detection if AST
    parsing fails.

    Args:
        code: The Python source code to analyze.

    Returns:
        A list of dicts with 'function', 'line', and 'code' keys
        describing each dangerous usage found.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return _check_dangerous_functions_string(code)

    issues: List[Dict[str, Any]] = []
    lines = code.splitlines()

    for node in ast.walk(tree):
        # Check function calls
        if isinstance(node, ast.Call):
            func_name = _get_attribute_name(node.func)
            if func_name is not None:
                # Check dangerous builtins
                base_name = func_name.split('.')[-1]
                if base_name in DANGEROUS_BUILTINS:
                    line_no = node.lineno
                    line_text = lines[line_no - 1] if line_no <= len(lines) else ''
                    issues.append(
                        {
                            'function': func_name,
                            'line': line_no,
                            'code': line_text.strip(),
                        }
                    )

                # Check dangerous attribute calls
                if func_name in DANGEROUS_ATTR_CALLS:
                    line_no = node.lineno
                    line_text = lines[line_no - 1] if line_no <= len(lines) else ''
                    issues.append(
                        {
                            'function': func_name,
                            'line': line_no,
                            'code': line_text.strip(),
                        }
                    )

                # Check subprocess.* calls
                if func_name.startswith('subprocess.'):
                    line_no = node.lineno
                    line_text = lines[line_no - 1] if line_no <= len(lines) else ''
                    issues.append(
                        {
                            'function': func_name,
                            'line': line_no,
                            'code': line_text.strip(),
                        }
                    )

        # Check dangerous dunder attribute accesses
        if isinstance(node, ast.Attribute):
            if node.attr in DANGEROUS_DUNDERS:
                line_no = node.lineno
                line_text = lines[line_no - 1] if line_no <= len(lines) else ''
                issues.append(
                    {
                        'function': node.attr,
                        'line': line_no,
                        'code': line_text.strip(),
                    }
                )

    return issues


def _check_dangerous_functions_string(code: str) -> List[Dict[str, Any]]:
    """Fallback string-based check for dangerous functions when AST parsing fails.

    Args:
        code: The Python source code to analyze.

    Returns:
        A list of dicts with 'function', 'line', and 'code' keys
        describing each dangerous usage found.
    """
    issues: List[Dict[str, Any]] = []
    lines = code.splitlines()

    all_patterns = set()
    all_patterns.update(DANGEROUS_BUILTINS)
    all_patterns.update(DANGEROUS_ATTR_CALLS)
    all_patterns.update(DANGEROUS_DUNDERS)
    # Add subprocess pattern
    all_patterns.add('subprocess.')

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        for pattern in all_patterns:
            if pattern in stripped:
                issues.append(
                    {
                        'function': pattern,
                        'line': line_no,
                        'code': stripped,
                    }
                )

    return issues


def get_fix_suggestion(issue: Dict[str, Any]) -> str:
    """Map a detected issue to a human-readable fix suggestion.

    Args:
        issue: A dict describing the issue, with at least a 'function' key.

    Returns:
        A string with a suggested fix for the issue.
    """
    function = issue.get('function', '')

    suggestions = {
        'exec': 'Remove exec() call. Dynamic code execution is not allowed.',
        'eval': 'Remove eval() call. Use literal values or ast.literal_eval() instead.',
        'compile': 'Remove compile() call. Dynamic code compilation is not allowed.',
        'getattr': 'Remove getattr() call. Use direct attribute access instead.',
        'setattr': 'Remove setattr() call. Use direct attribute assignment instead.',
        'delattr': 'Remove delattr() call. Use del statement on known attributes instead.',
        'vars': 'Remove vars() call. Use explicit attribute access instead.',
        '__import__': 'Remove __import__() call. Import statements are not allowed.',
        'breakpoint': 'Remove breakpoint() call. Debugging is not allowed in diagram code.',
        'open': 'Remove open() call. File I/O is not allowed in diagram code.',
        'globals': 'Remove globals() call. Accessing global scope is not allowed.',
        'locals': 'Remove locals() call. Accessing local scope is not allowed.',
        'spawn': 'Remove spawn() call. Process spawning is not allowed.',
        'os.system': 'Remove os.system() call. Shell command execution is not allowed.',
        'os.popen': 'Remove os.popen() call. Shell command execution is not allowed.',
        'pickle.loads': 'Remove pickle.loads() call. Deserialization is not allowed.',
        'pickle.load': 'Remove pickle.load() call. Deserialization is not allowed.',
        '__dict__': 'Remove __dict__ access. Direct dictionary access on objects is not allowed.',
        '__builtins__': 'Remove __builtins__ access. Accessing built-in scope is not allowed.',
        '__class__': 'Remove __class__ access. Class introspection is not allowed.',
        '__subclasses__': 'Remove __subclasses__() access. Class hierarchy traversal is not allowed.',
        '__bases__': 'Remove __bases__ access. Class hierarchy inspection is not allowed.',
        '__globals__': 'Remove __globals__ access. Accessing global scope is not allowed.',
        '__mro__': 'Remove __mro__ access. Method resolution order inspection is not allowed.',
    }

    # Check for subprocess.* pattern
    if function.startswith('subprocess.'):
        return 'Remove subprocess usage. Running external processes is not allowed.'

    return suggestions.get(
        function, f'Remove usage of {function}. This function is not allowed in diagram code.'
    )


async def validate_syntax(code: str) -> Tuple[bool, Optional[str]]:
    """Validate Python syntax and reject import statements.

    Parses the code with ast.parse() to check for syntax errors, then
    walks the AST to reject any import statements.

    Args:
        code: The Python source code to validate.

    Returns:
        A tuple of (is_valid, error_message). Returns (True, None) if
        the code is valid, or (False, error_message) if there are issues.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return (False, f'Syntax error: {e}')

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = ''
            if isinstance(node, ast.Import):
                module = ', '.join(alias.name for alias in node.names)
            else:
                module = node.module or ''
            return (False, f'Import statements are not allowed: {module}')

    return (True, None)


async def check_security(code: str) -> List[SecurityIssue]:
    """Check code for security issues using bandit and dangerous function detection.

    Writes the code to a temporary file, runs bandit's security analysis,
    and also checks for dangerous function calls.

    Args:
        code: The Python source code to scan.

    Returns:
        A list of SecurityIssue objects describing any security issues found.
    """
    issues: List[SecurityIssue] = []
    tmp_path = None

    try:
        # Write code to a temporary file for bandit analysis
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp_file:
            tmp_file.write(code)
            tmp_path = tmp_file.name

        # Run bandit security scanner
        try:
            from bandit.core import manager as bandit_manager

            b_mgr = bandit_manager.BanditManager(bandit_manager.BanditConfig(), 'file')
            b_mgr.discover_files([tmp_path])
            b_mgr.run_tests()

            for item in b_mgr.get_issue_list():
                issues.append(
                    SecurityIssue(
                        severity=item.severity,
                        confidence=item.confidence,
                        line=item.lineno,
                        issue_text=item.text,
                        issue_type=item.test_id,
                    )
                )
        except Exception:
            # If bandit fails, continue with dangerous function checks
            pass

        # Check for dangerous functions
        dangerous = check_dangerous_functions(code)
        for item in dangerous:
            issues.append(
                SecurityIssue(
                    severity='HIGH',
                    confidence='HIGH',
                    line=item.get('line', 0),
                    issue_text=f'Dangerous function call: {item.get("function", "unknown")}',
                    issue_type='dangerous_function',
                )
            )

    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return issues


async def count_code_metrics(code: str) -> CodeMetrics:
    """Count code metrics for the given source code.

    Args:
        code: The Python source code to analyze.

    Returns:
        A CodeMetrics object with line counts and comment ratio.
    """
    lines = code.splitlines()
    total_lines = len(lines)
    blank_lines = 0
    comment_lines = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank_lines += 1
        elif stripped.startswith('#'):
            comment_lines += 1

    code_lines = total_lines - blank_lines - comment_lines
    comment_ratio = (comment_lines / total_lines * 100.0) if total_lines > 0 else 0.0

    return CodeMetrics(
        total_lines=total_lines,
        code_lines=code_lines,
        comment_lines=comment_lines,
        blank_lines=blank_lines,
        comment_ratio=comment_ratio,
    )


async def scan_python_code(code: str) -> CodeScanResult:
    """Perform a complete security scan of Python code.

    Orchestrates metrics collection, syntax validation, and security
    checking into a single scan result.

    Args:
        code: The Python source code to scan.

    Returns:
        A CodeScanResult with the combined results of all checks.
    """
    metrics = await count_code_metrics(code)
    syntax_valid, error_message = await validate_syntax(code)

    if not syntax_valid:
        return CodeScanResult(
            has_errors=True,
            syntax_valid=False,
            security_issues=[],
            error_message=error_message,
            metrics=metrics,
        )

    security_issues = await check_security(code)

    return CodeScanResult(
        has_errors=len(security_issues) > 0,
        syntax_valid=True,
        security_issues=security_issues,
        error_message=None,
        metrics=metrics,
    )
