#!/usr/bin/env python3
"""
Route Structure Compliance Testing

Validates that all feature slices follow the standardized route organization pattern:
- crud_routes.py for API endpoints and database operations
- form_routes.py for HTMX partials, modals, and UI forms
- Correct API endpoint patterns (/api/list, /api/create, etc.)
- Proper Tabulator integration with standard response formats
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Set, Any

import pytest


class RouteStructureComplianceChecker:
    """Check route structure compliance across feature slices."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.features_dir = self.project_root / "app" / "features"
        self.violations = []

    def find_route_directories(self) -> List[Path]:
        """Find all routes directories in features."""
        return list(self.features_dir.glob("*/*/routes"))

    def check_route_file_separation(self) -> List[Dict]:
        """Verify crud_routes.py and form_routes.py exist and are properly separated."""
        violations = []

        for routes_dir in self.find_route_directories():
            if not routes_dir.is_dir():
                continue

            crud_routes = routes_dir / "crud_routes.py"
            form_routes = routes_dir / "form_routes.py"

            # Check if both files exist
            if not crud_routes.exists() or not form_routes.exists():
                # Allow for simple modules with only one routes file
                if (routes_dir / "routes.py").exists():
                    continue

                violations.append({
                    'type': 'missing_route_files',
                    'directory': str(routes_dir.relative_to(self.project_root)),
                    'issue': f'Missing crud_routes.py or form_routes.py (found: {list(routes_dir.glob("*.py"))})',
                    'severity': 'medium'
                })
                continue

            # Check __init__.py properly imports both
            init_file = routes_dir / "__init__.py"
            if init_file.exists():
                content = init_file.read_text()
                if "crud_router" not in content or "form_router" not in content:
                    violations.append({
                        'type': 'missing_router_imports',
                        'file': str(init_file.relative_to(self.project_root)),
                        'issue': '__init__.py must import both crud_router and form_router',
                        'severity': 'high'
                    })

        return violations

    def check_crud_routes_patterns(self) -> List[Dict]:
        """Verify crud_routes.py follows standard API patterns."""
        violations = []

        for routes_dir in self.find_route_directories():
            crud_routes = routes_dir / "crud_routes.py"
            if not crud_routes.exists():
                continue

            try:
                content = crud_routes.read_text()
                tree = ast.parse(content)

                # Check for standard API endpoints
                endpoints = self._extract_route_endpoints(tree)

                # Check for /api/list endpoint (for Tabulator)
                has_list_api = any('/list' in ep or '/api/list' in ep for ep in endpoints)

                if has_list_api:
                    # Verify list endpoint returns simple array (not wrapped)
                    if not self._check_list_endpoint_returns_array(tree, content):
                        violations.append({
                            'type': 'incorrect_api_response_format',
                            'file': str(crud_routes.relative_to(self.project_root)),
                            'issue': 'List API endpoint must return simple array, not wrapped in pagination object',
                            'severity': 'high',
                            'fix': 'Return: return result  # Not: return {"data": result}'
                        })

                # Check for HTMX partials in crud_routes (anti-pattern)
                if self._has_template_response(tree):
                    violations.append({
                        'type': 'template_in_crud_routes',
                        'file': str(crud_routes.relative_to(self.project_root)),
                        'issue': 'crud_routes.py should not have TemplateResponse (move to form_routes.py)',
                        'severity': 'medium'
                    })

            except Exception as e:
                violations.append({
                    'type': 'parse_error',
                    'file': str(crud_routes.relative_to(self.project_root)),
                    'issue': f'Failed to parse: {e}'
                })

        return violations

    def check_form_routes_patterns(self) -> List[Dict]:
        """Verify form_routes.py follows standard UI patterns."""
        violations = []

        for routes_dir in self.find_route_directories():
            form_routes = routes_dir / "form_routes.py"
            if not form_routes.exists():
                continue

            try:
                content = form_routes.read_text()
                tree = ast.parse(content)

                # Check for database operations in form_routes (anti-pattern)
                if self._has_direct_db_operations(tree, content):
                    violations.append({
                        'type': 'db_operations_in_form_routes',
                        'file': str(form_routes.relative_to(self.project_root)),
                        'issue': 'form_routes.py should not have direct database operations (use service layer)',
                        'severity': 'medium'
                    })

                # Check for proper TemplateResponse usage
                if not self._has_template_response(tree):
                    # Form routes should have templates
                    violations.append({
                        'type': 'missing_templates_in_form_routes',
                        'file': str(form_routes.relative_to(self.project_root)),
                        'issue': 'form_routes.py should return TemplateResponse for UI rendering',
                        'severity': 'low'
                    })

            except Exception as e:
                violations.append({
                    'type': 'parse_error',
                    'file': str(form_routes.relative_to(self.project_root)),
                    'issue': f'Failed to parse: {e}'
                })

        return violations

    def check_tabulator_integration(self) -> List[Dict]:
        """Verify Tabulator table integration follows standards."""
        violations = []

        # Find all static/js/*-table.js files
        for table_js in self.features_dir.glob("*/*/static/js/*-table.js"):
            try:
                content = table_js.read_text()

                # Check for required patterns
                checks = [
                    ('initialize function', r'window\.initialize\w+Table\s*=\s*function'),
                    ('advancedTableConfig', r'\.\.\.advancedTableConfig'),
                    ('ajaxURL pattern', r'ajaxURL:\s*["\']/.*/api/list'),
                    ('global registry', r'window\.appTables\['),
                    ('exportTable function', r'window\.exportTable\s*=\s*function'),
                    ('DOMContentLoaded', r'document\.addEventListener\(["\']DOMContentLoaded'),
                ]

                for check_name, pattern in checks:
                    if not re.search(pattern, content):
                        violations.append({
                            'type': 'missing_table_pattern',
                            'file': str(table_js.relative_to(self.project_root)),
                            'issue': f'Missing required pattern: {check_name}',
                            'pattern': pattern,
                            'severity': 'high'
                        })

                # Check for anti-patterns
                anti_patterns = [
                    ('custom showToast', r'function\s+showToast\s*\(', 'Use table-base.js showToast'),
                    ('inline styles', r'style\s*=\s*["\']', 'Use CSS classes, not inline styles'),
                    ('fixed width on all columns', r'width:\s*\d+.*width:\s*\d+.*width:\s*\d+', 'Use minWidth for flexible columns'),
                ]

                for pattern_name, pattern, fix in anti_patterns:
                    if re.search(pattern, content):
                        violations.append({
                            'type': 'table_anti_pattern',
                            'file': str(table_js.relative_to(self.project_root)),
                            'issue': f'Anti-pattern detected: {pattern_name}',
                            'fix': fix,
                            'severity': 'medium'
                        })

            except Exception as e:
                violations.append({
                    'type': 'parse_error',
                    'file': str(table_js.relative_to(self.project_root)),
                    'issue': f'Failed to parse: {e}'
                })

        return violations

    def _extract_route_endpoints(self, tree: ast.AST) -> List[str]:
        """Extract route endpoint paths from AST."""
        endpoints = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == 'router' and node.attr in ['get', 'post', 'put', 'delete']:
                    # Find the decorator with path
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.FunctionDef):
                            for decorator in parent.decorator_list:
                                if isinstance(decorator, ast.Call):
                                    if decorator.args:
                                        if isinstance(decorator.args[0], ast.Constant):
                                            endpoints.append(decorator.args[0].value)
        return endpoints

    def _check_list_endpoint_returns_array(self, tree: ast.AST, content: str) -> bool:
        """Check if list endpoint returns simple array."""
        # Look for return statements in list endpoint
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if 'list' in node.name.lower():
                    for child in ast.walk(node):
                        if isinstance(child, ast.Return):
                            # Check if return value is NOT a dict with 'data' key
                            if isinstance(child.value, ast.Dict):
                                for key in child.value.keys:
                                    if isinstance(key, ast.Constant) and key.value == 'data':
                                        return False  # Wrapped in data object - BAD
        return True  # Simple array - GOOD

    def _has_template_response(self, tree: ast.AST) -> bool:
        """Check if file uses TemplateResponse."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == 'TemplateResponse':
                return True
            if isinstance(node, ast.Attribute) and node.attr == 'TemplateResponse':
                return True
        return False

    def _has_direct_db_operations(self, tree: ast.AST, content: str) -> bool:
        """Check for direct database operations (anti-pattern in form routes)."""
        # Look for session.add, session.commit, session.delete
        patterns = ['session.add(', 'session.commit(', 'session.delete(', 'db.add(', 'db.commit(', 'db.delete(']
        return any(pattern in content for pattern in patterns)

    def run_all_checks(self) -> Dict[str, Any]:
        """Run all compliance checks."""
        all_violations = []

        all_violations.extend(self.check_route_file_separation())
        all_violations.extend(self.check_crud_routes_patterns())
        all_violations.extend(self.check_form_routes_patterns())
        all_violations.extend(self.check_tabulator_integration())

        return {
            'total_violations': len(all_violations),
            'violations': all_violations,
            'is_compliant': len(all_violations) == 0
        }


# Pytest test cases
class TestRouteStructureCompliance:
    """Pytest tests for route structure compliance."""

    @pytest.fixture
    def checker(self):
        return RouteStructureComplianceChecker()

    def test_route_file_separation(self, checker):
        """Test that routes are properly separated into crud and form files."""
        violations = checker.check_route_file_separation()
        assert len(violations) == 0, f"Route file separation violations:\n" + "\n".join(
            f"  - {v['directory']}: {v['issue']}" for v in violations
        )

    def test_crud_routes_patterns(self, checker):
        """Test that crud_routes.py follows standard patterns."""
        violations = checker.check_crud_routes_patterns()
        assert len(violations) == 0, f"CRUD routes pattern violations:\n" + "\n".join(
            f"  - {v['file']}: {v['issue']}" for v in violations
        )

    def test_form_routes_patterns(self, checker):
        """Test that form_routes.py follows standard patterns."""
        violations = checker.check_form_routes_patterns()
        assert len(violations) == 0, f"Form routes pattern violations:\n" + "\n".join(
            f"  - {v['file']}: {v['issue']}" for v in violations
        )

    def test_tabulator_integration(self, checker):
        """Test that Tabulator tables follow standard integration patterns."""
        violations = checker.check_tabulator_integration()
        assert len(violations) == 0, f"Tabulator integration violations:\n" + "\n".join(
            f"  - {v['file']}: {v['issue']}" for v in violations
        )

    def test_full_compliance(self, checker):
        """Run full compliance check."""
        results = checker.run_all_checks()
        assert results['is_compliant'], f"Found {results['total_violations']} violations"


if __name__ == "__main__":
    checker = RouteStructureComplianceChecker()
    results = checker.run_all_checks()

    print("=" * 60)
    print("Route Structure Compliance Check")
    print("=" * 60)
    print(f"Total Violations: {results['total_violations']}")
    print()

    if results['violations']:
        # Group by severity
        by_severity = {'high': [], 'medium': [], 'low': []}
        for v in results['violations']:
            severity = v.get('severity', 'medium')
            by_severity[severity].append(v)

        for severity in ['high', 'medium', 'low']:
            if by_severity[severity]:
                print(f"🚨 {severity.upper()} Violations:")
                for v in by_severity[severity]:
                    print(f"  File: {v.get('file', v.get('directory', 'unknown'))}")
                    print(f"  Issue: {v['issue']}")
                    if 'fix' in v:
                        print(f"  Fix: {v['fix']}")
                    print()
    else:
        print("✅ All checks passed!")

    exit(0 if results['is_compliant'] else 1)
