#!/usr/bin/env python3
"""
Global Admin Compliance Testing

Validates that global admin patterns are consistently applied across the codebase:
- Correct use of is_global_admin() helper function
- Proper global admin authorization on protected routes
- Consistent tenant isolation patterns for global vs tenant admins
- Global admin cross-tenant operations follow security patterns
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Set, Any

import pytest


class GlobalAdminComplianceChecker:
    """Check global admin implementation compliance across the codebase."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.app_dir = self.project_root / "app"
        self.features_dir = self.app_dir / "features"
        self.violations = []

    def find_route_files(self) -> List[Path]:
        """Find all route files in features."""
        route_files = []
        for pattern in ["**/routes.py", "**/routes/*.py"]:
            route_files.extend(self.features_dir.glob(pattern))
        return [f for f in route_files if f.is_file()]

    def check_global_admin_helper_usage(self) -> List[Dict]:
        """Verify routes use is_global_admin() helper instead of inline checks."""
        violations = []

        for route_file in self.find_route_files():
            try:
                content = route_file.read_text()
                tree = ast.parse(content)

                # Check for inline global admin checks (anti-pattern)
                inline_patterns = [
                    r'user\.role\s*==\s*["\']global_admin["\']',
                    r'current_user\.tenant_id\s*==\s*["\']global["\']',
                    r'role\s*==\s*["\']global_admin["\'].*tenant_id\s*==\s*["\']global["\']',
                ]

                has_inline_check = any(re.search(pattern, content) for pattern in inline_patterns)

                # Check if is_global_admin is imported
                has_helper_import = 'is_global_admin' in content

                if has_inline_check and not has_helper_import:
                    violations.append({
                        'type': 'inline_global_admin_check',
                        'file': str(route_file.relative_to(self.project_root)),
                        'issue': 'Using inline global admin check instead of is_global_admin() helper',
                        'severity': 'medium',
                        'fix': 'Import and use: from app.features.core.route_imports import is_global_admin'
                    })

                # Check if helper is imported but from wrong location
                if 'is_global_admin' in content and 'route_imports import is_global_admin' not in content:
                    # Check if it's imported from elsewhere
                    import_pattern = r'from\s+[\w.]+\s+import\s+.*is_global_admin'
                    if re.search(import_pattern, content) and 'route_imports' not in content:
                        violations.append({
                            'type': 'wrong_import_location',
                            'file': str(route_file.relative_to(self.project_root)),
                            'issue': 'is_global_admin should be imported from app.features.core.route_imports',
                            'severity': 'low',
                            'fix': 'Use: from app.features.core.route_imports import is_global_admin'
                        })

            except Exception as e:
                violations.append({
                    'type': 'parse_error',
                    'file': str(route_file.relative_to(self.project_root)),
                    'issue': f'Failed to parse: {e}'
                })

        return violations

    def check_protected_routes_authorization(self) -> List[Dict]:
        """Verify protected routes use proper authorization dependencies."""
        violations = []

        for route_file in self.find_route_files():
            # Skip if not in administration/tenants (main area requiring global admin)
            if 'tenants' not in str(route_file):
                continue

            try:
                content = route_file.read_text()
                tree = ast.parse(content)

                # Check for routes that should require global admin
                tenant_management_endpoints = self._find_tenant_management_endpoints(tree)

                for endpoint in tenant_management_endpoints:
                    # Check if it uses get_global_admin_user dependency
                    if not self._uses_global_admin_dependency(endpoint):
                        violations.append({
                            'type': 'missing_global_admin_authorization',
                            'file': str(route_file.relative_to(self.project_root)),
                            'function': endpoint['name'],
                            'issue': 'Tenant management endpoint should use get_global_admin_user dependency',
                            'severity': 'high',
                            'fix': 'Add parameter: admin: User = Depends(get_global_admin_user)'
                        })

            except Exception as e:
                violations.append({
                    'type': 'parse_error',
                    'file': str(route_file.relative_to(self.project_root)),
                    'issue': f'Failed to parse: {e}'
                })

        return violations

    def check_cross_tenant_operations(self) -> List[Dict]:
        """Verify cross-tenant operations follow security patterns."""
        violations = []

        for route_file in self.find_route_files():
            try:
                content = route_file.read_text()

                # Check for target_tenant_id pattern (cross-tenant operations)
                if 'target_tenant_id' in content:
                    # Verify it checks is_global_admin before allowing
                    if not re.search(r'is_global_admin\s*\(', content):
                        violations.append({
                            'type': 'unsafe_cross_tenant_operation',
                            'file': str(route_file.relative_to(self.project_root)),
                            'issue': 'Cross-tenant operation (target_tenant_id) without global admin check',
                            'severity': 'critical',
                            'fix': 'Add: is_global_admin(current_user) check before allowing cross-tenant operations'
                        })

                    # Verify tenant validation
                    if 'target_tenant_id' in content and 'get_available_tenants' not in content:
                        violations.append({
                            'type': 'missing_tenant_validation',
                            'file': str(route_file.relative_to(self.project_root)),
                            'issue': 'Cross-tenant operation without tenant validation',
                            'severity': 'high',
                            'fix': 'Use service.get_available_tenants_for_*_forms() to validate target tenant'
                        })

            except Exception as e:
                violations.append({
                    'type': 'parse_error',
                    'file': str(route_file.relative_to(self.project_root)),
                    'issue': f'Failed to parse: {e}'
                })

        return violations

    def check_tenant_isolation_in_services(self) -> List[Dict]:
        """Verify services properly handle global admin tenant isolation."""
        violations = []

        service_files = list(self.features_dir.glob("**/services.py"))

        for service_file in service_files:
            try:
                content = service_file.read_text()
                tree = ast.parse(content)

                # Check if service inherits from BaseService
                if 'BaseService' not in content:
                    continue

                # Check for proper tenant_id handling
                # Services should convert "global" to None for global admins
                if 'tenant_id' in content:
                    # Check if it handles global tenant properly
                    has_global_handling = (
                        'tenant_id == "global"' in content or
                        'tenant_id = None' in content or
                        'if tenant_id' in content
                    )

                    if not has_global_handling and 'self.tenant_id' in content:
                        # Verify it's using BaseService which handles this automatically
                        if not re.search(r'class\s+\w+Service\s*\(\s*BaseService', content):
                            violations.append({
                                'type': 'missing_global_tenant_handling',
                                'file': str(service_file.relative_to(self.project_root)),
                                'issue': 'Service uses tenant_id but does not handle "global" tenant conversion',
                                'severity': 'high',
                                'fix': 'Inherit from BaseService or manually convert tenant_id="global" to None'
                            })

            except Exception as e:
                violations.append({
                    'type': 'parse_error',
                    'file': str(service_file.relative_to(self.project_root)),
                    'issue': f'Failed to parse: {e}'
                })

        return violations

    def _find_tenant_management_endpoints(self, tree: ast.AST) -> List[Dict]:
        """Find endpoints that perform tenant management operations."""
        endpoints = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function has router decorator
                for decorator in node.decorator_list:
                    if self._is_router_decorator(decorator):
                        # Check if it's a POST/PUT/DELETE (mutating operation)
                        if self._is_mutating_operation(decorator):
                            endpoints.append({
                                'name': node.name,
                                'node': node
                            })

        return endpoints

    def _is_router_decorator(self, decorator: ast.AST) -> bool:
        """Check if decorator is a router decorator."""
        if isinstance(decorator, ast.Attribute):
            return isinstance(decorator.value, ast.Name) and decorator.value.id == 'router'
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                return isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == 'router'
        return False

    def _is_mutating_operation(self, decorator: ast.AST) -> bool:
        """Check if decorator is for a mutating operation (POST/PUT/DELETE)."""
        if isinstance(decorator, ast.Attribute):
            return decorator.attr in ['post', 'put', 'delete']
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                return decorator.func.attr in ['post', 'put', 'delete']
        return False

    def _uses_global_admin_dependency(self, endpoint: Dict) -> bool:
        """Check if endpoint uses get_global_admin_user dependency."""
        node = endpoint['node']

        # Check function parameters for Depends(get_global_admin_user)
        for arg in node.args.args:
            if arg.annotation:
                # Look for Depends in annotation
                annotation_str = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                if 'get_global_admin_user' in annotation_str:
                    return True

        return False

    def run_all_checks(self) -> Dict[str, Any]:
        """Run all global admin compliance checks."""
        all_violations = []

        all_violations.extend(self.check_global_admin_helper_usage())
        all_violations.extend(self.check_protected_routes_authorization())
        all_violations.extend(self.check_cross_tenant_operations())
        all_violations.extend(self.check_tenant_isolation_in_services())

        return {
            'total_violations': len(all_violations),
            'violations': all_violations,
            'is_compliant': len(all_violations) == 0
        }


# Pytest test cases
class TestGlobalAdminCompliance:
    """Pytest tests for global admin compliance."""

    @pytest.fixture
    def checker(self):
        return GlobalAdminComplianceChecker()

    def test_global_admin_helper_usage(self, checker):
        """Test that routes use is_global_admin() helper consistently."""
        violations = checker.check_global_admin_helper_usage()
        assert len(violations) == 0, f"Global admin helper usage violations:\n" + "\n".join(
            f"  - {v['file']}: {v['issue']}" for v in violations
        )

    def test_protected_routes_authorization(self, checker):
        """Test that protected routes use proper authorization."""
        violations = checker.check_protected_routes_authorization()
        assert len(violations) == 0, f"Protected route authorization violations:\n" + "\n".join(
            f"  - {v['file']} ({v.get('function', 'unknown')}): {v['issue']}" for v in violations
        )

    def test_cross_tenant_operations(self, checker):
        """Test that cross-tenant operations follow security patterns."""
        violations = checker.check_cross_tenant_operations()
        # Filter out non-critical violations for this test
        critical_violations = [v for v in violations if v.get('severity') == 'critical']
        assert len(critical_violations) == 0, f"Cross-tenant operation security violations:\n" + "\n".join(
            f"  - {v['file']}: {v['issue']}" for v in critical_violations
        )

    def test_tenant_isolation_in_services(self, checker):
        """Test that services properly handle tenant isolation."""
        violations = checker.check_tenant_isolation_in_services()
        assert len(violations) == 0, f"Service tenant isolation violations:\n" + "\n".join(
            f"  - {v['file']}: {v['issue']}" for v in violations
        )

    def test_full_compliance(self, checker):
        """Run full global admin compliance check."""
        results = checker.run_all_checks()
        # Allow some low-severity violations
        critical_violations = [v for v in results['violations'] if v.get('severity') in ['critical', 'high']]
        assert len(critical_violations) == 0, f"Found {len(critical_violations)} critical/high severity violations"


if __name__ == "__main__":
    checker = GlobalAdminComplianceChecker()
    results = checker.run_all_checks()

    print("=" * 60)
    print("Global Admin Compliance Check")
    print("=" * 60)
    print(f"Total Violations: {results['total_violations']}")
    print()

    if results['violations']:
        # Group by severity
        by_severity = {'critical': [], 'high': [], 'medium': [], 'low': []}
        for v in results['violations']:
            severity = v.get('severity', 'medium')
            by_severity[severity].append(v)

        for severity in ['critical', 'high', 'medium', 'low']:
            if by_severity[severity]:
                print(f"🚨 {severity.upper()} Violations:")
                for v in by_severity[severity]:
                    print(f"  File: {v['file']}")
                    print(f"  Issue: {v['issue']}")
                    if 'fix' in v:
                        print(f"  Fix: {v['fix']}")
                    if 'function' in v:
                        print(f"  Function: {v['function']}")
                    print()
    else:
        print("✅ All checks passed!")

    exit(0 if results['is_compliant'] else 1)
