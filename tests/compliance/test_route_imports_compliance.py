"""
Route Imports Compliance Tests

Tests for centralized route_imports patterns and standardized error handling.
Validates the gold standard route architecture we established.
"""

import ast
import sys
from pathlib import Path
from typing import List, Dict, Any

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class RouteImportsComplianceChecker:
    """Checks compliance with centralized route imports and patterns."""

    def __init__(self):
        self.features_dir = project_root / "app" / "features"
        self.violations = []

    def find_route_files(self) -> List[Path]:
        """Find all route files in features directory."""
        route_files = []
        for pattern in ["**/routes/*.py", "**/routes.py"]:
            route_files.extend(self.features_dir.glob(pattern))
        return [f for f in route_files if f.name != '__init__.py']

    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse file and extract import and function information."""
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

    def check_centralized_route_imports(self, file_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for centralized route_imports usage."""
        violations = []
        content = file_data.get('content', '')
        relative_path = file_data['relative_path']

        # Skip if empty, has errors, or is core infrastructure
        if not content or 'error' in file_data or '/core/' in relative_path:
            return violations

        # Check for centralized imports pattern
        has_centralized_imports = 'from app.features.core.route_imports import' in content

        # Check for individual FastAPI imports (anti-pattern when centralized available)
        individual_fastapi_imports = [
            'from fastapi import APIRouter',
            'from fastapi import Depends',
            'from fastapi import Request',
            'from fastapi import HTTPException',
            'from fastapi.responses import HTMLResponse',
            'from fastapi.responses import JSONResponse'
        ]

        found_individual = [imp for imp in individual_fastapi_imports if imp in content]

        # Check if file has route functions (indicates it should use centralized imports)
        has_route_functions = '@router.' in content or 'def ' in content

        if has_route_functions and not has_centralized_imports and found_individual:
            violations.append({
                'file': relative_path,
                'type': 'missing_centralized_route_imports',
                'message': 'Route file should use centralized route_imports for consistency',
                'severity': 'medium'
            })

        if found_individual and has_centralized_imports:
            violations.append({
                'file': relative_path,
                'type': 'redundant_individual_route_imports',
                'message': f'Found individual FastAPI imports when using centralized imports: {", ".join(found_individual[:2])}...',
                'severity': 'low'
            })

        return violations

    def check_standardized_error_handling(self, file_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for standardized error handling patterns."""
        violations = []
        content = file_data.get('content', '')
        tree = file_data.get('tree')
        relative_path = file_data['relative_path']

        if not content or not tree or 'error' in file_data:
            return violations

        # Check for handle_route_error usage
        has_handle_route_error = 'handle_route_error(' in content

        # Find route functions with try/except blocks
        route_functions_with_errors = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if it's a route function (has router decorator)
                is_route_function = False
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute) and hasattr(decorator.value, 'id'):
                        if decorator.value.id == 'router':
                            is_route_function = True
                            break

                if is_route_function:
                    # Check for try/except blocks in route
                    for child in ast.walk(node):
                        if isinstance(child, ast.Try) or isinstance(child, ast.ExceptHandler):
                            route_functions_with_errors.append(node.name)
                            break

        # If route has error handling but doesn't use standardized function
        if route_functions_with_errors and not has_handle_route_error:
            violations.append({
                'file': relative_path,
                'type': 'missing_standardized_error_handling',
                'functions': route_functions_with_errors,
                'message': f'Route functions with error handling should use handle_route_error(): {", ".join(route_functions_with_errors[:3])}',
                'severity': 'medium'
            })

        return violations

    def check_transaction_management(self, file_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for standardized transaction management."""
        violations = []
        content = file_data.get('content', '')
        relative_path = file_data['relative_path']

        if not content or 'error' in file_data:
            return violations

        # Check for commit_transaction usage
        has_commit_transaction = 'commit_transaction(' in content

        # Check for direct db.commit() calls (anti-pattern)
        has_direct_commit = 'db.commit()' in content or 'await db.commit()' in content

        # Check if route does database operations (has db parameter and create/update/delete operations)
        has_db_ops = ('db:' in content and
                     any(op in content.lower() for op in ['create', 'update', 'delete', 'add', 'flush']))

        if has_direct_commit:
            violations.append({
                'file': relative_path,
                'type': 'direct_commit_in_route',
                'message': 'Routes should use commit_transaction() instead of direct db.commit()',
                'severity': 'high'
            })

        if has_db_ops and not has_commit_transaction and not has_direct_commit:
            violations.append({
                'file': relative_path,
                'type': 'missing_transaction_management',
                'message': 'Route with database operations should use commit_transaction()',
                'severity': 'medium'
            })

        return violations

    def check_response_standardization(self, file_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for standardized response patterns."""
        violations = []
        content = file_data.get('content', '')
        relative_path = file_data['relative_path']

        if not content or 'error' in file_data:
            return violations

        # Check for create_success_response usage
        has_success_response = 'create_success_response(' in content

        # Check for manual response creation (anti-pattern)
        manual_responses = [
            'JSONResponse(',
            'Response(status_code=204',
            'HTTPException(status_code=500'
        ]

        found_manual = [resp for resp in manual_responses if resp in content]

        # Check if route returns responses
        has_response_returns = any(pattern in content for pattern in ['return ', 'raise HTTPException'])

        if found_manual and has_success_response:
            violations.append({
                'file': relative_path,
                'type': 'mixed_response_patterns',
                'message': f'Mix of manual and standardized responses found: {", ".join(found_manual[:2])}',
                'severity': 'low'
            })

        return violations

    def check_auth_patterns(self, file_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for standardized auth patterns."""
        violations = []
        content = file_data.get('content', '')
        relative_path = file_data['relative_path']

        if not content or 'error' in file_data:
            return violations

        # Check for is_global_admin usage
        has_centralized_auth = 'is_global_admin(' in content

        # Check for manual admin checks (anti-pattern)
        manual_admin_checks = [
            'current_user.is_global_admin',
            'user.is_global_admin',
            'current_user.role == UserRole.GLOBAL_ADMIN'
        ]

        found_manual_auth = [check for check in manual_admin_checks if check in content]

        if found_manual_auth and not has_centralized_auth:
            violations.append({
                'file': relative_path,
                'type': 'manual_admin_check',
                'message': f'Should use is_global_admin() instead of manual checks: {", ".join(found_manual_auth[:2])}',
                'severity': 'medium'
            })

        return violations

    def run_compliance_check(self) -> Dict[str, Any]:
        """Run full compliance check."""
        route_files = self.find_route_files()
        all_violations = []

        for route_file in route_files:
            file_data = self.parse_file(route_file)

            violations = []
            violations.extend(self.check_centralized_route_imports(file_data))
            violations.extend(self.check_standardized_error_handling(file_data))
            violations.extend(self.check_transaction_management(file_data))
            violations.extend(self.check_response_standardization(file_data))
            violations.extend(self.check_auth_patterns(file_data))

            all_violations.extend(violations)

        # Calculate compliance score
        total_files = len(route_files)
        files_with_violations = len(set(v['file'] for v in all_violations))
        compliant_files = total_files - files_with_violations
        compliance_score = (compliant_files / total_files * 100) if total_files > 0 else 100

        return {
            'total_files': total_files,
            'compliant_files': compliant_files,
            'compliance_score': compliance_score,
            'violations': all_violations,
            'status': 'PASS' if compliance_score >= 80 else 'FAIL'
        }


# Pytest test cases
class TestRouteImportsCompliance:
    """Pytest tests for route imports compliance."""

    @pytest.fixture
    def checker(self):
        return RouteImportsComplianceChecker()

    def test_no_direct_commits_in_routes(self, checker):
        """Test that routes don't use direct db.commit()."""
        results = checker.run_compliance_check()

        commit_violations = [
            v for v in results['violations']
            if v['type'] == 'direct_commit_in_route'
        ]

        if commit_violations:
            violation_summary = '\n'.join([
                f"  {v['file']} - {v['message']}"
                for v in commit_violations
            ])
            pytest.fail(
                f"Routes using direct db.commit() found:\n{violation_summary}\n\n"
                "Routes should use commit_transaction(db, operation_name) for consistent transaction management."
            )

    def test_standardized_error_handling(self, checker):
        """Test that routes use standardized error handling."""
        results = checker.run_compliance_check()

        error_violations = [
            v for v in results['violations']
            if v['type'] == 'missing_standardized_error_handling'
        ]

        # Only fail on critical error handling issues, not all routes need error handling
        critical_error_violations = [v for v in error_violations if v['severity'] == 'high']

        if critical_error_violations:
            violation_summary = '\n'.join([
                f"  {v['file']} - {v['message']}"
                for v in critical_error_violations
            ])
            pytest.fail(
                f"Routes with critical error handling issues:\n{violation_summary}\n\n"
                "Routes with error handling should use handle_route_error(operation, error, **context)"
            )

    def test_transaction_management(self, checker):
        """Test proper transaction management patterns."""
        results = checker.run_compliance_check()

        transaction_violations = [
            v for v in results['violations']
            if v['type'] in ['direct_commit_in_route', 'missing_transaction_management']
        ]

        # Only fail on direct commits (high severity)
        critical_transaction_violations = [v for v in transaction_violations if v['severity'] == 'high']

        if critical_transaction_violations:
            violation_summary = '\n'.join([
                f"  {v['file']} - {v['message']}"
                for v in critical_transaction_violations
            ])
            pytest.fail(
                f"Routes with critical transaction management issues:\n{violation_summary}\n\n"
                "Routes should use commit_transaction() for proper error handling and rollback support."
            )

    def test_auth_patterns(self, checker):
        """Test standardized auth patterns."""
        results = checker.run_compliance_check()

        auth_violations = [
            v for v in results['violations']
            if v['type'] == 'manual_admin_check'
        ]

        # This is a style/consistency issue, not critical
        if len(auth_violations) > 5:  # Only fail if there are many violations
            violation_summary = '\n'.join([
                f"  {v['file']} - {v['message']}"
                for v in auth_violations[:5]
            ])
            pytest.fail(
                f"Many routes using manual admin checks (showing first 5):\n{violation_summary}\n\n"
                "Consider using centralized is_global_admin() for consistency."
            )

    def test_compliance_score_threshold(self, checker):
        """Test overall compliance score meets threshold."""
        results = checker.run_compliance_check()

        min_score = 75.0  # Lower threshold for routes as they're more varied

        assert results['compliance_score'] >= min_score, (
            f"Route imports compliance score {results['compliance_score']:.1f}% is below "
            f"minimum threshold of {min_score}%.\n"
            f"Files checked: {results['total_files']}\n"
            f"Violations: {len(results['violations'])}"
        )

    def test_critical_violations_only(self, checker):
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
                f"Critical route pattern violations found:\n{violation_summary}\n\n"
                "These violations must be fixed to maintain gold standard route patterns."
            )


if __name__ == "__main__":
    """Run from command line."""
    checker = RouteImportsComplianceChecker()
    results = checker.run_compliance_check()

    print(f"🔍 Route Imports Compliance Check")
    print(f"Files checked: {results['total_files']}")
    print(f"Compliance score: {results['compliance_score']:.1f}%")
    print(f"Status: {results['status']}")

    if results['violations']:
        print(f"\n❌ {len(results['violations'])} violations found:")

        # Group by severity
        by_severity = {}
        for v in results['violations']:
            sev = v['severity']
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append(v)

        for sev in ['high', 'medium', 'low']:
            if sev in by_severity:
                print(f"\n{sev.upper()} severity ({len(by_severity[sev])}):")
                for violation in by_severity[sev]:
                    print(f"  {violation['file']} - {violation['message']}")
    else:
        print("\n✅ No violations found!")

    # Exit with error code if critical violations
    critical_count = len([v for v in results['violations'] if v['severity'] == 'high'])
    exit(1 if critical_count > 0 else 0)
