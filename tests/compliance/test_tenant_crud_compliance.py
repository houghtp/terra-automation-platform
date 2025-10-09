"""
Automated Tenant CRUD Compliance Testing

This module provides automated tests to ensure all tenant-aware CRUD operations
follow the standardized patterns for proper tenant isolation and data integrity.

These tests should be run in CI/CD to prevent regression.
"""

import ast
import os
import sys
import importlib
import inspect
from pathlib import Path
from typing import List, Dict, Set, Any, Optional

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.features.core.base_service import BaseService
    from app.deps.tenant import tenant_dependency
except ImportError:
    # For running outside of full environment
    AsyncSession = None
    BaseService = None
    tenant_dependency = None


class TenantCRUDComplianceChecker:
    """
    Automated compliance checker for tenant CRUD operations.

    Validates:
    1. Routes use tenant_dependency
    2. Services inherit from BaseService (for CRUD operations)
    3. Services use flush() not commit()
    4. Proper tenant isolation patterns
    """

    def __init__(self):
        self.app_dir = Path(__file__).parent.parent.parent / "app"
        self.features_dir = self.app_dir / "features"
        self.violations = []

    def get_route_files(self) -> List[Path]:
        """Get all route files in the features directory."""
        route_files = []
        for route_file in self.features_dir.rglob("routes.py"):
            # Skip core and non-feature routes
            if "core" not in str(route_file) and "features" in str(route_file):
                route_files.append(route_file)
        return route_files

    def get_service_files(self) -> List[Path]:
        """Get all service files in the features directory."""
        service_files = []
        for service_file in self.features_dir.rglob("services.py"):
            # Skip core services
            if "core" not in str(service_file) and "features" in str(service_file):
                service_files.append(service_file)
        return service_files

    def parse_file(self, file_path: Path) -> ast.AST:
        """Parse Python file into AST."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return ast.parse(content)
        except Exception as e:
            self.violations.append({
                'file': str(file_path),
                'type': 'parse_error',
                'message': f"Failed to parse file: {e}"
            })
            return None

    def check_route_tenant_dependency(self, file_path: Path, tree: ast.AST) -> List[Dict]:
        """Check if routes properly use tenant_dependency."""
        violations = []

        # Check if tenant_dependency is imported
        has_tenant_import = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if (node.module == "app.deps.tenant" and
                    any(alias.name == "tenant_dependency" for alias in node.names)):
                    has_tenant_import = True
                    break

        # Find route functions that should use tenant_dependency
        route_functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function has router decorator
                for decorator in node.decorator_list:
                    if (isinstance(decorator, ast.Attribute) and
                        isinstance(decorator.value, ast.Name) and
                        decorator.value.id == "router"):
                        route_functions.append(node)
                        break

        # Check each route function for tenant_dependency usage
        for func in route_functions:
            # Skip auth routes and global admin routes
            if ("login" in func.name.lower() or
                "logout" in func.name.lower() or
                "register" in func.name.lower()):
                continue

            # Skip if it's clearly a non-tenant route
            if ("health" in func.name.lower() or
                "ping" in func.name.lower() or
                "version" in func.name.lower()):
                continue

            # Check if function parameters include tenant dependency
            has_tenant_param = False
            for arg in func.args.args:
                if arg.arg == "tenant":
                    # Look for Depends(tenant_dependency) in defaults
                    for default in func.args.defaults:
                        if (isinstance(default, ast.Call) and
                            isinstance(default.func, ast.Name) and
                            default.func.id == "Depends"):
                            if (len(default.args) > 0 and
                                isinstance(default.args[0], ast.Name) and
                                default.args[0].id == "tenant_dependency"):
                                has_tenant_param = True
                                break

            if not has_tenant_param and has_tenant_import:
                violations.append({
                    'file': str(file_path),
                    'type': 'missing_tenant_dependency',
                    'function': func.name,
                    'line': func.lineno,
                    'message': f"Route function '{func.name}' should use tenant: str = Depends(tenant_dependency)"
                })
            elif not has_tenant_import:
                violations.append({
                    'file': str(file_path),
                    'type': 'missing_tenant_import',
                    'function': func.name,
                    'line': func.lineno,
                    'message': f"File should import tenant_dependency from app.deps.tenant"
                })

        return violations

    def check_service_base_inheritance(self, file_path: Path, tree: ast.AST) -> List[Dict]:
        """Check if services properly inherit from BaseService."""
        violations = []

        # Skip read-only services that don't need BaseService
        file_content = str(file_path)
        if any(readonly in file_content.lower() for readonly in ['audit', 'log', 'dashboard']):
            return violations

        # Check if BaseService is imported
        has_baseservice_import = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if (node.module == "app.features.core.base_service" and
                    any(alias.name == "BaseService" for alias in node.names)):
                    has_baseservice_import = True
                    break

        # Find service classes
        service_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if "service" in node.name.lower():
                    service_classes.append(node)

        # Check each service class
        for cls in service_classes:
            # Skip if it's clearly a read-only service
            if any(readonly in cls.name.lower() for readonly in ['audit', 'log', 'dashboard']):
                continue

            # Check if class inherits from BaseService
            inherits_baseservice = False
            for base in cls.bases:
                if isinstance(base, ast.Subscript):
                    # BaseService[Model] pattern
                    if (isinstance(base.value, ast.Name) and
                        base.value.id == "BaseService"):
                        inherits_baseservice = True
                        break
                elif isinstance(base, ast.Name) and base.id == "BaseService":
                    inherits_baseservice = True
                    break

            if not inherits_baseservice and has_baseservice_import:
                violations.append({
                    'file': str(file_path),
                    'type': 'missing_baseservice_inheritance',
                    'class': cls.name,
                    'line': cls.lineno,
                    'message': f"Service class '{cls.name}' should inherit from BaseService[Model]"
                })
            elif not has_baseservice_import and not any(readonly in cls.name.lower() for readonly in ['audit', 'log', 'dashboard']):
                violations.append({
                    'file': str(file_path),
                    'type': 'missing_baseservice_import',
                    'class': cls.name,
                    'line': cls.lineno,
                    'message': f"File should import BaseService from app.features.core.base_service"
                })

        return violations

    def check_service_transaction_handling(self, file_path: Path, tree: ast.AST) -> List[Dict]:
        """Check if services use flush() instead of commit()."""
        violations = []

        # Skip read-only services
        file_content = str(file_path)
        if any(readonly in file_content.lower() for readonly in ['audit', 'log', 'dashboard']):
            return violations

        # Find commit() calls in service methods
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for self.db.commit() or self.session.commit()
                if (isinstance(node.func, ast.Attribute) and
                    node.func.attr == "commit" and
                    isinstance(node.func.value, ast.Attribute)):

                    # Check if it's self.db.commit() or self.session.commit()
                    if (isinstance(node.func.value.value, ast.Name) and
                        node.func.value.value.id == "self" and
                        node.func.value.attr in ["db", "session"]):

                        violations.append({
                            'file': str(file_path),
                            'type': 'using_commit_instead_of_flush',
                            'line': node.lineno,
                            'message': f"Service should use flush() instead of commit() at line {node.lineno}. Routes handle commits."
                        })

        return violations

    def check_tenant_isolation_patterns(self, file_path: Path, tree: ast.AST) -> List[Dict]:
        """Check for proper tenant isolation patterns in services."""
        violations = []

        # Check for tenant_id parameter in __init__ methods
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef) and
                node.name == "__init__" and
                "service" in str(file_path).lower()):

                # Skip read-only services
                if any(readonly in str(file_path).lower() for readonly in ['audit', 'log', 'dashboard']):
                    continue

                # Check if __init__ takes tenant_id parameter
                has_tenant_param = False
                for arg in node.args.args:
                    if "tenant" in arg.arg:
                        has_tenant_param = True
                        break

                if not has_tenant_param:
                    violations.append({
                        'file': str(file_path),
                        'type': 'missing_tenant_parameter',
                        'method': '__init__',
                        'line': node.lineno,
                        'message': f"Service __init__ should accept tenant_id parameter for proper isolation"
                    })

        return violations

    def run_compliance_check(self) -> Dict[str, Any]:
        """Run full compliance check and return results."""
        self.violations = []
        results = {
            'total_files_checked': 0,
            'route_files_checked': 0,
            'service_files_checked': 0,
            'violations': [],
            'compliance_score': 0.0,
            'status': 'PASS'
        }

        # Check route files
        route_files = self.get_route_files()
        for route_file in route_files:
            tree = self.parse_file(route_file)
            if tree:
                violations = self.check_route_tenant_dependency(route_file, tree)
                self.violations.extend(violations)
                results['route_files_checked'] += 1

        # Check service files
        service_files = self.get_service_files()
        for service_file in service_files:
            tree = self.parse_file(service_file)
            if tree:
                violations = []
                violations.extend(self.check_service_base_inheritance(service_file, tree))
                violations.extend(self.check_service_transaction_handling(service_file, tree))
                violations.extend(self.check_tenant_isolation_patterns(service_file, tree))
                self.violations.extend(violations)
                results['service_files_checked'] += 1

        results['total_files_checked'] = results['route_files_checked'] + results['service_files_checked']
        results['violations'] = self.violations

        # Calculate compliance score
        total_checks = results['total_files_checked']
        violation_count = len(self.violations)
        if total_checks > 0:
            results['compliance_score'] = max(0.0, (total_checks - violation_count) / total_checks * 100)

        # Set status
        if violation_count == 0:
            results['status'] = 'PASS'
        elif results['compliance_score'] >= 80:
            results['status'] = 'WARNING'
        else:
            results['status'] = 'FAIL'

        return results


# Test Classes for Pytest

class TestTenantCRUDCompliance:
    """Pytest test cases for tenant CRUD compliance."""

    @pytest.fixture
    def compliance_checker(self):
        """Create compliance checker instance."""
        return TenantCRUDComplianceChecker()

    def test_no_critical_violations(self, compliance_checker):
        """Test that there are no critical compliance violations."""
        results = compliance_checker.run_compliance_check()

        # Critical violations that should fail CI/CD
        critical_violations = [
            v for v in results['violations']
            if v['type'] in [
                'using_commit_instead_of_flush',
                'missing_tenant_dependency',
                'missing_baseservice_inheritance'
            ]
        ]

        if critical_violations:
            violation_summary = "\n".join([
                f"  {v['file']}:{v.get('line', '?')} - {v['message']}"
                for v in critical_violations
            ])
            pytest.fail(
                f"Critical tenant CRUD compliance violations found:\n{violation_summary}\n\n"
                f"These violations must be fixed to ensure proper tenant isolation and data integrity."
            )

    def test_compliance_score_threshold(self, compliance_checker):
        """Test that compliance score meets minimum threshold."""
        results = compliance_checker.run_compliance_check()

        min_compliance_score = 85.0  # Require 85% compliance

        assert results['compliance_score'] >= min_compliance_score, (
            f"Compliance score {results['compliance_score']:.1f}% is below minimum threshold of {min_compliance_score}%.\n"
            f"Violations found: {len(results['violations'])}\n"
            f"Files checked: {results['total_files_checked']}"
        )

    def test_no_commit_in_services(self, compliance_checker):
        """Test that services don't use commit() directly."""
        results = compliance_checker.run_compliance_check()

        commit_violations = [
            v for v in results['violations']
            if v['type'] == 'using_commit_instead_of_flush'
        ]

        if commit_violations:
            violation_summary = "\n".join([
                f"  {v['file']}:{v['line']} - {v['message']}"
                for v in commit_violations
            ])
            pytest.fail(
                f"Services using commit() instead of flush() found:\n{violation_summary}\n\n"
                f"Services should use flush() and let routes handle commits for proper transaction management."
            )

    def test_tenant_dependency_usage(self, compliance_checker):
        """Test that routes properly use tenant_dependency."""
        results = compliance_checker.run_compliance_check()

        tenant_violations = [
            v for v in results['violations']
            if v['type'] in ['missing_tenant_dependency', 'missing_tenant_import']
        ]

        if tenant_violations:
            violation_summary = "\n".join([
                f"  {v['file']}:{v.get('line', '?')} - {v['message']}"
                for v in tenant_violations
            ])
            pytest.fail(
                f"Routes missing proper tenant_dependency usage:\n{violation_summary}\n\n"
                f"All tenant-aware routes should use: tenant: str = Depends(tenant_dependency)"
            )

    def test_generate_compliance_report(self, compliance_checker):
        """Generate compliance report for documentation."""
        results = compliance_checker.run_compliance_check()

        report = f"""
# Automated Tenant CRUD Compliance Report

## Summary
- **Total Files Checked**: {results['total_files_checked']}
  - Route Files: {results['route_files_checked']}
  - Service Files: {results['service_files_checked']}
- **Compliance Score**: {results['compliance_score']:.1f}%
- **Status**: {results['status']}
- **Violations Found**: {len(results['violations'])}

## Violations by Type
"""

        # Group violations by type
        violations_by_type = {}
        for violation in results['violations']:
            vtype = violation['type']
            if vtype not in violations_by_type:
                violations_by_type[vtype] = []
            violations_by_type[vtype].append(violation)

        for vtype, violations in violations_by_type.items():
            report += f"\n### {vtype.replace('_', ' ').title()} ({len(violations)} violations)\n"
            for violation in violations:
                report += f"- `{violation['file']}:{violation.get('line', '?')}` - {violation['message']}\n"

        if not results['violations']:
            report += "\n🎉 **No violations found! All tenant CRUD operations are compliant.**\n"

        # Save report to file
        report_path = Path(__file__).parent.parent.parent / "docs" / "compliance-report.md"
        with open(report_path, 'w') as f:
            f.write(report)

        print(f"Compliance report generated: {report_path}")


if __name__ == "__main__":
    """Run compliance check from command line."""
    checker = TenantCRUDComplianceChecker()
    results = checker.run_compliance_check()

    print(f"Tenant CRUD Compliance Check Results:")
    print(f"Files Checked: {results['total_files_checked']}")
    print(f"Compliance Score: {results['compliance_score']:.1f}%")
    print(f"Status: {results['status']}")
    print(f"Violations: {len(results['violations'])}")

    if results['violations']:
        print("\nViolations Found:")
        for violation in results['violations']:
            print(f"  {violation['file']}:{violation.get('line', '?')} - {violation['message']}")
    else:
        print("\n🎉 No violations found! All tenant CRUD operations are compliant.")

    # Exit with non-zero code if critical violations found
    critical_count = len([
        v for v in results['violations']
        if v['type'] in [
            'using_commit_instead_of_flush',
            'missing_tenant_dependency',
            'missing_baseservice_inheritance'
        ]
    ])

    if critical_count > 0:
        exit(1)
    else:
        exit(0)
