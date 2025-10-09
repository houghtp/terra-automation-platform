"""
Enhanced Service Imports Compliance Tests

Tests for enhanced BaseService patterns and centralized sqlalchemy_imports usage.
Validates the gold standard service architecture we established.
"""

import ast
import sys
from pathlib import Path
from typing import List, Dict, Any

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class ServiceImportsComplianceChecker:
    """Checks compliance with enhanced service patterns."""

    def __init__(self):
        self.features_dir = project_root / "app" / "features"
        self.violations = []

    def find_service_files(self) -> List[Path]:
        """Find all service files in features directory."""
        service_files = []
        for pattern in ["**/services.py", "**/crud_services.py", "**/form_services.py", "**/dashboard_services.py"]:
            service_files.extend(self.features_dir.glob(pattern))
        return [f for f in service_files if "core" not in str(f)]

    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse file and extract import and class information."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            tree = ast.parse(content)

            return {
                'content': content,
                'tree': tree,
                'file_path': file_path,
                'relative_path': str(file_path.relative_to(project_root))
            }
        except Exception as e:
            return {
                'error': str(e),
                'file_path': file_path,
                'relative_path': str(file_path.relative_to(project_root))
            }

    def check_centralized_imports(self, file_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for centralized sqlalchemy_imports usage."""
        violations = []
        content = file_data.get('content', '')
        relative_path = file_data['relative_path']

        # Skip if empty or has errors
        if not content or 'error' in file_data:
            return violations

        # Check for centralized imports pattern
        has_centralized_imports = 'from app.features.core.sqlalchemy_imports import *' in content

        # Check for individual SQLAlchemy imports (anti-pattern)
        individual_imports = [
            'from sqlalchemy import',
            'from sqlalchemy.orm import',
            'from sqlalchemy.ext.asyncio import',
            'import sqlalchemy'
        ]

        found_individual = [imp for imp in individual_imports if imp in content]

        if not has_centralized_imports and any('Service' in line for line in content.split('\n')):
            violations.append({
                'file': relative_path,
                'type': 'missing_centralized_imports',
                'message': 'Service file should use centralized sqlalchemy_imports',
                'severity': 'high'
            })

        if found_individual and has_centralized_imports:
            violations.append({
                'file': relative_path,
                'type': 'redundant_individual_imports',
                'message': f'Found individual SQLAlchemy imports when using centralized imports: {found_individual}',
                'severity': 'medium'
            })
        elif found_individual and not has_centralized_imports:
            violations.append({
                'file': relative_path,
                'type': 'should_use_centralized_imports',
                'message': f'Should use centralized sqlalchemy_imports instead of individual imports: {found_individual}',
                'severity': 'high'
            })

        return violations

    def check_enhanced_base_service(self, file_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for enhanced BaseService usage patterns."""
        violations = []
        tree = file_data.get('tree')
        relative_path = file_data['relative_path']

        if not tree or 'error' in file_data:
            return violations

        # Find service classes
        service_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith('Service'):
                service_classes.append(node)

        for service_class in service_classes:
            # Skip utility/static-only services
            if any(pattern in service_class.name for pattern in ['Auth', 'Utility', 'Helper']):
                continue

            # Check for BaseService inheritance
            inherits_base = False
            for base in service_class.bases:
                if isinstance(base, ast.Name) and base.id == 'BaseService':
                    inherits_base = True
                elif isinstance(base, ast.Subscript):
                    if isinstance(base.value, ast.Name) and base.value.id == 'BaseService':
                        inherits_base = True

            if not inherits_base:
                violations.append({
                    'file': relative_path,
                    'type': 'missing_enhanced_base_service',
                    'service': service_class.name,
                    'message': f'Service {service_class.name} should inherit from BaseService[Model]',
                    'severity': 'high'
                })

        return violations

    def check_proper_logging(self, file_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for proper logging patterns."""
        violations = []
        content = file_data.get('content', '')
        relative_path = file_data['relative_path']

        if not content or 'error' in file_data:
            return violations

        # Check for centralized logger usage
        has_centralized_logger = 'logger = get_logger(__name__)' in content
        has_old_logging = 'import logging' in content or 'logging.getLogger' in content

        if has_old_logging:
            violations.append({
                'file': relative_path,
                'type': 'old_logging_pattern',
                'message': 'Service should use centralized get_logger from sqlalchemy_imports',
                'severity': 'medium'
            })

        if 'class ' in content and 'Service' in content and not has_centralized_logger:
            violations.append({
                'file': relative_path,
                'type': 'missing_centralized_logger',
                'message': 'Service should use logger = get_logger(__name__) pattern',
                'severity': 'low'
            })

        return violations

    def run_compliance_check(self) -> Dict[str, Any]:
        """Run full compliance check."""
        service_files = self.find_service_files()
        all_violations = []

        for service_file in service_files:
            file_data = self.parse_file(service_file)

            violations = []
            violations.extend(self.check_centralized_imports(file_data))
            violations.extend(self.check_enhanced_base_service(file_data))
            violations.extend(self.check_proper_logging(file_data))

            all_violations.extend(violations)

        # Calculate compliance score
        total_files = len(service_files)
        files_with_violations = len(set(v['file'] for v in all_violations))
        compliant_files = total_files - files_with_violations
        compliance_score = (compliant_files / total_files * 100) if total_files > 0 else 100

        return {
            'total_files': total_files,
            'compliant_files': compliant_files,
            'compliance_score': compliance_score,
            'violations': all_violations,
            'status': 'PASS' if compliance_score >= 85 else 'FAIL'
        }


# Pytest test cases
class TestServiceImportsCompliance:
    """Pytest tests for service imports compliance."""

    @pytest.fixture
    def checker(self):
        return ServiceImportsComplianceChecker()

    def test_centralized_imports_usage(self, checker):
        """Test that services use centralized sqlalchemy_imports."""
        results = checker.run_compliance_check()

        import_violations = [
            v for v in results['violations']
            if v['type'] in ['missing_centralized_imports', 'should_use_centralized_imports']
        ]

        if import_violations:
            violation_summary = '\n'.join([
                f"  {v['file']} - {v['message']}"
                for v in import_violations
            ])
            pytest.fail(
                f"Services not using centralized sqlalchemy_imports:\n{violation_summary}\n\n"
                "All services should use: from app.features.core.sqlalchemy_imports import *"
            )

    def test_enhanced_base_service_usage(self, checker):
        """Test that services properly inherit from enhanced BaseService."""
        results = checker.run_compliance_check()

        base_service_violations = [
            v for v in results['violations']
            if v['type'] == 'missing_enhanced_base_service'
        ]

        if base_service_violations:
            violation_summary = '\n'.join([
                f"  {v['file']} - Service: {v['service']} - {v['message']}"
                for v in base_service_violations
            ])
            pytest.fail(
                f"Services not inheriting from enhanced BaseService:\n{violation_summary}\n\n"
                "CRUD services should inherit from BaseService[Model] for tenant isolation and query patterns"
            )

    def test_compliance_score_threshold(self, checker):
        """Test overall compliance score meets threshold."""
        results = checker.run_compliance_check()

        min_score = 85.0

        assert results['compliance_score'] >= min_score, (
            f"Service imports compliance score {results['compliance_score']:.1f}% is below "
            f"minimum threshold of {min_score}%.\n"
            f"Files checked: {results['total_files']}\n"
            f"Violations: {len(results['violations'])}"
        )

    def test_no_critical_violations(self, checker):
        """Test that there are no critical violations."""
        results = checker.run_compliance_check()

        critical_violations = [
            v for v in results['violations']
            if v['severity'] == 'high'
        ]

        if critical_violations:
            violation_summary = '\n'.join([
                f"  {v['file']} - {v['message']}"
                for v in critical_violations
            ])
            pytest.fail(
                f"Critical service imports violations found:\n{violation_summary}\n\n"
                "These violations must be fixed to maintain gold standard service patterns."
            )


if __name__ == "__main__":
    """Run from command line."""
    checker = ServiceImportsComplianceChecker()
    results = checker.run_compliance_check()

    print(f"🔍 Enhanced Service Imports Compliance Check")
    print(f"Files checked: {results['total_files']}")
    print(f"Compliance score: {results['compliance_score']:.1f}%")
    print(f"Status: {results['status']}")

    if results['violations']:
        print(f"\n❌ {len(results['violations'])} violations found:")
        for violation in results['violations']:
            print(f"  {violation['file']} - {violation['message']} ({violation['severity']})")
    else:
        print("\n✅ No violations found!")

    # Exit with error code if critical violations
    critical_count = len([v for v in results['violations'] if v['severity'] == 'high'])
    exit(1 if critical_count > 0 else 0)
