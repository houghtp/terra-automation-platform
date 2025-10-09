#!/usr/bin/env python3
"""
Standalone tenant CRUD compliance checker.
Analyzes Python files without importing the full app.
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Set, Any, Optional


class TenantCRUDComplianceChecker:
    """Checks tenant CRUD compliance without app imports."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations = []

    def find_python_files(self) -> List[Path]:
        """Find all Python files in features directory."""
        features_dir = self.project_root / "app" / "features"
        return list(features_dir.rglob("*.py"))

    def analyze_service_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a service file for compliance."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            tree = ast.parse(content)

            # Find service classes
            service_classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.endswith('Service'):
                    # Check if it inherits from BaseService (including generic forms)
                    inherits_base_service = any(
                        (isinstance(base, ast.Name) and base.id == 'BaseService') or
                        (isinstance(base, ast.Attribute) and base.attr == 'BaseService') or
                        (isinstance(base, ast.Subscript) and
                         isinstance(base.value, ast.Name) and base.value.id == 'BaseService') or
                        (isinstance(base, ast.Subscript) and
                         isinstance(base.value, ast.Attribute) and base.value.attr == 'BaseService')
                        for base in node.bases
                    )

                    # Check if service only has static methods (utility class)
                    method_nodes = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    static_only = len(method_nodes) > 0 and all(
                        any(
                            (isinstance(d, ast.Name) and d.id == 'staticmethod') or
                            (isinstance(d, ast.Attribute) and d.attr == 'staticmethod')
                            for d in method.decorator_list
                        )
                        for method in method_nodes
                    )

                    # Check for BaseService import
                    has_base_service_import = 'from app.features.core.base_service import BaseService' in content

                    service_classes.append({
                        'name': node.name,
                        'inherits_base_service': inherits_base_service,
                        'has_base_service_import': has_base_service_import,
                        'static_only': static_only
                    })

            return {
                'file_path': str(file_path.relative_to(self.project_root)),
                'service_classes': service_classes,
                'has_content': len(content.strip()) > 0
            }
        except Exception as e:
            return {
                'file_path': str(file_path.relative_to(self.project_root)),
                'error': str(e),
                'service_classes': []
            }

    def check_compliance(self) -> Dict[str, Any]:
        """Check compliance across all service files."""
        python_files = self.find_python_files()
        service_files = [f for f in python_files if f.name == 'services.py']

        total_services = 0
        compliant_services = 0
        violations = []

        for file_path in service_files:
            analysis = self.analyze_service_file(file_path)

            if 'error' in analysis:
                violations.append({
                    'file': analysis['file_path'],
                    'type': 'parse_error',
                    'issue': analysis['error']
                })
                continue

            for service_class in analysis['service_classes']:
                total_services += 1

                # Special cases that should not inherit from BaseService
                special_cases = ['AuthService', 'TenantManagementService']

                if service_class['name'] in special_cases or service_class.get('static_only', False):
                    compliant_services += 1  # These are compliant by design
                    continue

                if not service_class['inherits_base_service']:
                    violations.append({
                        'file': analysis['file_path'],
                        'type': 'missing_base_service_inheritance',
                        'service': service_class['name'],
                        'issue': f"Service {service_class['name']} should inherit from BaseService"
                    })
                elif not service_class['has_base_service_import']:
                    violations.append({
                        'file': analysis['file_path'],
                        'type': 'missing_base_service_import',
                        'service': service_class['name'],
                        'issue': f"File missing BaseService import for {service_class['name']}"
                    })
                else:
                    compliant_services += 1

        compliance_score = (compliant_services / total_services * 100) if total_services > 0 else 100

        return {
            'total_services': total_services,
            'compliant_services': compliant_services,
            'compliance_score': compliance_score,
            'violations': violations
        }


def main():
    """Run compliance check."""
    project_root = Path(__file__).parent.parent
    checker = TenantCRUDComplianceChecker(project_root)

    print("🔍 Running Tenant CRUD Compliance Check...")
    print("=" * 60)

    results = checker.check_compliance()

    print(f"📊 Total Services: {results['total_services']}")
    print(f"✅ Compliant Services: {results['compliant_services']}")
    print(f"📈 Compliance Score: {results['compliance_score']:.1f}%")
    print()

    if results['violations']:
        print(f"❌ Found {len(results['violations'])} violations:")
        print()
        for violation in results['violations']:
            print(f"  File: {violation['file']}")
            print(f"  Issue: {violation['issue']}")
            if 'service' in violation:
                print(f"  Service: {violation['service']}")
            print(f"  Type: {violation['type']}")
            print()
    else:
        print("🎉 No violations found! All services are compliant.")

    return len(results['violations'])


# Pytest test cases
import pytest


class TestBaseServiceCompliance:
    """Pytest tests for BaseService compliance."""

    @pytest.fixture
    def checker(self):
        project_root = Path(__file__).parent.parent.parent
        return TenantCRUDComplianceChecker(project_root)

    def test_all_services_inherit_base_service(self, checker):
        """Test that all CRUD services inherit from BaseService."""
        results = checker.check_compliance()

        inheritance_violations = [
            v for v in results['violations']
            if v['type'] == 'missing_base_service_inheritance'
        ]

        if inheritance_violations:
            violation_summary = '\n'.join([
                f"  {v['file']} - Service: {v['service']} - {v['issue']}"
                for v in inheritance_violations
            ])
            pytest.fail(
                f"Services not inheriting from BaseService found:\n{violation_summary}\n\n"
                "All CRUD services should inherit from BaseService[Model] for tenant isolation."
            )

    def test_base_service_imports_present(self, checker):
        """Test that files importing BaseService have proper imports."""
        results = checker.check_compliance()

        import_violations = [
            v for v in results['violations']
            if v['type'] == 'missing_base_service_import'
        ]

        if import_violations:
            violation_summary = '\n'.join([
                f"  {v['file']} - Service: {v['service']} - {v['issue']}"
                for v in import_violations
            ])
            pytest.fail(
                f"Services missing BaseService import:\n{violation_summary}\n\n"
                "Files with BaseService inheritance must import BaseService."
            )

    def test_compliance_score_threshold(self, checker):
        """Test that compliance score meets minimum threshold."""
        results = checker.check_compliance()

        min_compliance_score = 80.0

        assert results['compliance_score'] >= min_compliance_score, (
            f"BaseService compliance score {results['compliance_score']:.1f}% is below "
            f"minimum threshold of {min_compliance_score}%.\n"
            f"Total services: {results['total_services']}\n"
            f"Violations: {len(results['violations'])}"
        )


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
