#!/usr/bin/env python3
"""
Automated Logging Compliance Checker

Analyzes Python files to ensure consistent structlog usage across the platform.
Detects violations of logging standards and provides compliance scores.
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Set, Any, Optional


class LoggingComplianceChecker:
    """Checks logging compliance across the codebase."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations = []

    def find_python_files(self) -> List[Path]:
        """Find all Python files in features directory."""
        features_dir = self.project_root / "app" / "features"
        return list(features_dir.rglob("*.py"))

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a Python file for logging compliance."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Skip empty files
            if not content.strip():
                return {
                    'file_path': str(file_path.relative_to(self.project_root)),
                    'skip_reason': 'empty_file',
                    'is_compliant': True
                }

            tree = ast.parse(content)

            # Check imports
            has_logging_import = 'import logging' in content
            has_structlog_import = 'import structlog' in content

            # Check logger initialization patterns
            logger_patterns = self._analyze_logger_patterns(content, tree)

            # Check log call patterns
            log_calls = self._analyze_log_calls(tree)

            # Determine compliance
            is_core_infrastructure = self._is_core_infrastructure(file_path)
            compliance_issues = self._evaluate_compliance(
                file_path, has_logging_import, has_structlog_import,
                logger_patterns, log_calls, is_core_infrastructure
            )

            return {
                'file_path': str(file_path.relative_to(self.project_root)),
                'has_logging_import': has_logging_import,
                'has_structlog_import': has_structlog_import,
                'logger_patterns': logger_patterns,
                'log_calls': log_calls,
                'is_core_infrastructure': is_core_infrastructure,
                'compliance_issues': compliance_issues,
                'is_compliant': len(compliance_issues) == 0
            }
        except SyntaxError as e:
            # Handle syntax errors gracefully - skip these files
            return {
                'file_path': str(file_path.relative_to(self.project_root)),
                'skip_reason': f'syntax_error: {str(e)}',
                'is_compliant': True  # Skip from compliance checking
            }
        except Exception as e:
            return {
                'file_path': str(file_path.relative_to(self.project_root)),
                'error': str(e),
                'is_compliant': False
            }

    def _analyze_logger_patterns(self, content: str, tree: ast.AST) -> List[Dict[str, str]]:
        """Analyze logger initialization patterns."""
        patterns = []

        # Check for various logger assignment patterns
        logger_lines = [line for line in content.split('\\n') if 'logger =' in line]

        for line in logger_lines:
            line = line.strip()
            if 'logging.getLogger' in line:
                patterns.append({
                    'type': 'standard_logging',
                    'pattern': line,
                    'compliant': False
                })
            elif 'structlog.get_logger' in line:
                patterns.append({
                    'type': 'structlog',
                    'pattern': line,
                    'compliant': True
                })
            else:
                patterns.append({
                    'type': 'unknown',
                    'pattern': line,
                    'compliant': False
                })

        return patterns

    def _analyze_log_calls(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze logging method calls for structured logging patterns."""
        log_calls = {
            'total_calls': 0,
            'structured_calls': 0,
            'string_format_calls': 0,
            'exception_calls': 0,
            'methods_used': set()
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    # Check for logger.method() calls
                    if (isinstance(node.func.value, ast.Name) and
                        node.func.value.id == 'logger'):

                        method = node.func.attr
                        if method in ['debug', 'info', 'warning', 'error', 'critical']:
                            log_calls['total_calls'] += 1
                            log_calls['methods_used'].add(method)

                            # Check if it's structured (has keyword arguments)
                            if node.keywords:
                                log_calls['structured_calls'] += 1

                            # Check for string formatting (f-strings, .format(), %)
                            if node.args and len(node.args) > 0:
                                first_arg = node.args[0]
                                if isinstance(first_arg, ast.JoinedStr):  # f-string
                                    log_calls['string_format_calls'] += 1
                                elif isinstance(first_arg, ast.Call):
                                    # Could be .format() call
                                    if (isinstance(first_arg.func, ast.Attribute) and
                                        first_arg.func.attr == 'format'):
                                        log_calls['string_format_calls'] += 1

                            # Check for exc_info parameter
                            for keyword in node.keywords:
                                if keyword.arg == 'exc_info':
                                    log_calls['exception_calls'] += 1

        log_calls['methods_used'] = list(log_calls['methods_used'])
        return log_calls

    def _is_core_infrastructure(self, file_path: Path) -> bool:
        """Check if file is core infrastructure that may use standard logging."""
        core_patterns = [
            'structured_logging.py',
            'logging.py',
            'bootstrap.py',
            'main.py'
        ]
        return any(pattern in str(file_path) for pattern in core_patterns)

    def _evaluate_compliance(
        self,
        file_path: Path,
        has_logging_import: bool,
        has_structlog_import: bool,
        logger_patterns: List[Dict],
        log_calls: Dict,
        is_core_infrastructure: bool
    ) -> List[Dict[str, str]]:
        """Evaluate compliance and return list of issues."""
        issues = []

        # Skip empty files or files without logging
        if not logger_patterns and log_calls['total_calls'] == 0:
            return issues

        # Core infrastructure files are exempt from structlog requirements
        if is_core_infrastructure:
            return issues

        # Check import compliance
        if has_logging_import and not is_core_infrastructure:
            issues.append({
                'type': 'import_violation',
                'issue': 'Uses standard logging import instead of structlog',
                'severity': 'high'
            })

        if not has_structlog_import and logger_patterns:
            issues.append({
                'type': 'missing_structlog_import',
                'issue': 'Missing structlog import but has logger usage',
                'severity': 'high'
            })

        # Check logger initialization patterns
        for pattern in logger_patterns:
            if not pattern['compliant']:
                issues.append({
                    'type': 'logger_init_violation',
                    'issue': f"Non-compliant logger initialization: {pattern['pattern']}",
                    'severity': 'high'
                })

        # Check structured logging usage
        if log_calls['total_calls'] > 0:
            structured_ratio = log_calls['structured_calls'] / log_calls['total_calls']
            if structured_ratio < 0.5:  # Less than 50% structured
                issues.append({
                    'type': 'structured_logging_violation',
                    'issue': f"Low structured logging usage: {structured_ratio:.1%} ({log_calls['structured_calls']}/{log_calls['total_calls']})",
                    'severity': 'medium'
                })

            # Check for excessive string formatting
            if log_calls['string_format_calls'] > log_calls['structured_calls']:
                issues.append({
                    'type': 'string_formatting_violation',
                    'issue': f"More string formatting than structured logging: {log_calls['string_format_calls']} vs {log_calls['structured_calls']}",
                    'severity': 'medium'
                })

        return issues

    def check_compliance(self) -> Dict[str, Any]:
        """Check compliance across all Python files."""
        python_files = self.find_python_files()

        total_files = 0
        compliant_files = 0
        all_violations = []
        file_results = []

        for file_path in python_files:
            analysis = self.analyze_file(file_path)
            file_results.append(analysis)

            if 'error' in analysis:
                all_violations.append({
                    'file': analysis['file_path'],
                    'type': 'parse_error',
                    'issue': analysis['error'],
                    'severity': 'critical'
                })
                continue

            # Skip files that don't need compliance checking
            if 'skip_reason' in analysis:
                continue

            # Only count files that actually use logging
            has_logging = (analysis['logger_patterns'] or
                          analysis['log_calls']['total_calls'] > 0)

            if has_logging:
                total_files += 1

                if analysis['is_compliant']:
                    compliant_files += 1
                else:
                    for issue in analysis['compliance_issues']:
                        all_violations.append({
                            'file': analysis['file_path'],
                            **issue
                        })

        compliance_score = (compliant_files / total_files * 100) if total_files > 0 else 100

        return {
            'total_files_with_logging': total_files,
            'compliant_files': compliant_files,
            'compliance_score': compliance_score,
            'violations': all_violations,
            'file_results': file_results
        }


def main():
    """Run logging compliance check."""
    project_root = Path(__file__).parent.parent
    checker = LoggingComplianceChecker(project_root)

    print("🔍 Running Logging Compliance Check...")
    print("=" * 60)

    results = checker.check_compliance()

    print(f"📊 Total Files with Logging: {results['total_files_with_logging']}")
    print(f"✅ Compliant Files: {results['compliant_files']}")
    print(f"📈 Compliance Score: {results['compliance_score']:.1f}%")
    print()

    # Group violations by severity
    violations_by_severity = {}
    for violation in results['violations']:
        severity = violation.get('severity', 'unknown')
        if severity not in violations_by_severity:
            violations_by_severity[severity] = []
        violations_by_severity[severity].append(violation)

    if results['violations']:
        print(f"❌ Found {len(results['violations'])} violations:")
        print()

        # Show critical issues first
        for severity in ['critical', 'high', 'medium', 'low']:
            if severity in violations_by_severity:
                print(f"🚨 {severity.upper()} Issues:")
                for violation in violations_by_severity[severity]:
                    print(f"  File: {violation['file']}")
                    print(f"  Issue: {violation['issue']}")
                    print(f"  Type: {violation['type']}")
                    print()
    else:
        print("🎉 No violations found! All files are compliant.")

    # Show summary statistics
    structlog_files = sum(1 for result in results['file_results']
                         if result.get('has_structlog_import', False))
    logging_files = sum(1 for result in results['file_results']
                       if result.get('has_logging_import', False))

    print("📊 Summary Statistics:")
    print(f"  Files using structlog: {structlog_files}")
    print(f"  Files using standard logging: {logging_files}")
    print(f"  Migration progress: {structlog_files}/{structlog_files + logging_files} ({structlog_files/(structlog_files + logging_files)*100 if (structlog_files + logging_files) > 0 else 0:.1f}%)")

    return len(results['violations'])


# Pytest test cases
import pytest


class TestLoggingCompliance:
    """Pytest tests for logging compliance."""

    @pytest.fixture
    def checker(self):
        project_root = Path(__file__).parent.parent.parent
        return LoggingComplianceChecker(project_root)

    def test_no_standard_logging_imports(self, checker):
        """Test that files don't use standard logging imports."""
        results = checker.check_compliance()

        import_violations = [
            v for v in results['violations']
            if v['type'] == 'import_violation'
        ]

        if import_violations:
            violation_summary = '\n'.join([
                f"  {v['file']} - {v['issue']}"
                for v in import_violations
            ])
            pytest.fail(
                f"Files using standard logging instead of structlog:\n{violation_summary}\n\n"
                "All files should use structlog for consistent structured logging."
            )

    def test_proper_logger_initialization(self, checker):
        """Test that loggers are properly initialized with structlog."""
        results = checker.check_compliance()

        init_violations = [
            v for v in results['violations']
            if v['type'] == 'logger_init_violation'
        ]

        if init_violations:
            violation_summary = '\n'.join([
                f"  {v['file']} - {v['issue']}"
                for v in init_violations
            ])
            pytest.fail(
                f"Files with non-compliant logger initialization:\n{violation_summary}\n\n"
                "Use: logger = structlog.get_logger(__name__)"
            )

    def test_structured_logging_usage(self, checker):
        """Test adequate structured logging usage."""
        results = checker.check_compliance()

        structured_violations = [
            v for v in results['violations']
            if v['type'] == 'structured_logging_violation' and v['severity'] == 'high'
        ]

        if structured_violations:
            violation_summary = '\n'.join([
                f"  {v['file']} - {v['issue']}"
                for v in structured_violations
            ])
            pytest.fail(
                f"Files with very low structured logging usage:\n{violation_summary}\n\n"
                "Use structured logging with keyword arguments: logger.info('message', key=value)"
            )

    def test_compliance_score_threshold(self, checker):
        """Test that compliance score meets minimum threshold."""
        results = checker.check_compliance()

        min_compliance_score = 75.0

        assert results['compliance_score'] >= min_compliance_score, (
            f"Logging compliance score {results['compliance_score']:.1f}% is below "
            f"minimum threshold of {min_compliance_score}%.\n"
            f"Files with logging: {results['total_files_with_logging']}\n"
            f"Violations: {len(results['violations'])}"
        )


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
