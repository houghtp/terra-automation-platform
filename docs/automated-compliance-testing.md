# Tenant CRUD Compliance CI/CD Configuration

## GitHub Actions Workflow

Create `.github/workflows/tenant-compliance.yml`:

```yaml
name: Tenant CRUD Compliance Check

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
    paths:
      - 'app/features/**/routes.py'
      - 'app/features/**/services.py'

jobs:
  compliance-check:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest
        pip install -r requirements.txt

    - name: Run Tenant CRUD Compliance Check
      run: |
        python tests/compliance/test_tenant_crud_compliance.py
        pytest tests/compliance/test_tenant_crud_compliance.py -v

    - name: Generate Compliance Report
      if: always()
      run: |
        pytest tests/compliance/test_tenant_crud_compliance.py::TestTenantCRUDCompliance::test_generate_compliance_report -v

    - name: Upload Compliance Report
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: compliance-report
        path: docs/compliance-report.md

    - name: Comment PR with Compliance Results
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          try {
            const report = fs.readFileSync('docs/compliance-report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Tenant CRUD Compliance Check Results\n\n${report}`
            });
          } catch (error) {
            console.log('No compliance report found');
          }
```

## Pre-commit Hook

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: tenant-crud-compliance
        name: Tenant CRUD Compliance Check
        entry: python tests/compliance/test_tenant_crud_compliance.py
        language: system
        files: ^app/features/.*(routes|services)\.py$
        pass_filenames: false
        always_run: false
```

## VSCode Settings

Add to `.vscode/settings.json`:

```json
{
  "python.testing.pytestArgs": [
    "tests/compliance/",
    "-v"
  ],
  "python.testing.unittestEnabled": false,
  "python.testing.pytestEnabled": true,
  "python.linting.enabled": true,
  "python.linting.pylintArgs": [
    "--load-plugins=tests.compliance.tenant_crud_linter"
  ]
}
```

## Make Commands

Add to `Makefile`:

```makefile
.PHONY: compliance-check compliance-report compliance-fix

compliance-check:
	@echo "Running Tenant CRUD Compliance Check..."
	python tests/compliance/test_tenant_crud_compliance.py
	pytest tests/compliance/test_tenant_crud_compliance.py -v

compliance-report:
	@echo "Generating Compliance Report..."
	pytest tests/compliance/test_tenant_crud_compliance.py::TestTenantCRUDCompliance::test_generate_compliance_report -v
	@echo "Report generated at docs/compliance-report.md"

compliance-fix:
	@echo "Running automated compliance fixes..."
	# Add automated fix scripts here

test-compliance: compliance-check
	@echo "Compliance tests completed"
```

## Development Workflow Integration

### 1. Developer Pre-commit
```bash
# Install pre-commit hook
pip install pre-commit
pre-commit install

# Run manually
pre-commit run tenant-crud-compliance --all-files
```

### 2. IDE Integration
- VSCode will automatically run compliance tests when testing
- Add compliance checks to your IDE's save actions

### 3. CI/CD Integration
- GitHub Actions runs on every PR touching routes/services
- Fails CI if critical violations found
- Generates compliance report as artifact
- Comments PR with results

## Usage Examples

### Command Line
```bash
# Quick compliance check
python tests/compliance/test_tenant_crud_compliance.py

# Full pytest run with verbose output
pytest tests/compliance/test_tenant_crud_compliance.py -v

# Generate report only
make compliance-report

# Check specific files
pytest tests/compliance/test_tenant_crud_compliance.py -k "test_no_commit_in_services"
```

### Expected Output
```
Tenant CRUD Compliance Check Results:
Files Checked: 15
Compliance Score: 90.0%
Status: PASS
Violations: 3

Violations Found:
  app/features/administration/api_keys/routes.py:161 - Route function 'create_api_key' should use tenant: str = Depends(tenant_dependency)
  app/features/administration/api_keys/services.py:45 - Service should use flush() instead of commit() at line 45
  app/features/administration/api_keys/services.py:12 - Service class 'APIKeyService' should inherit from BaseService[Model]
```

## Violation Types and Fixes

### Critical Violations (Fail CI)
1. **`using_commit_instead_of_flush`**
   - **Fix**: Change `await self.db.commit()` to `await self.db.flush()`
   - **Reason**: Routes should handle transaction commits

2. **`missing_tenant_dependency`**
   - **Fix**: Add `tenant: str = Depends(tenant_dependency)` to route parameters
   - **Reason**: Ensures proper tenant isolation

3. **`missing_baseservice_inheritance`**
   - **Fix**: Make service inherit from `BaseService[Model]`
   - **Reason**: Standardizes tenant-aware service patterns

### Warning Violations (Allow with lower compliance score)
1. **`missing_tenant_import`**
   - **Fix**: Add `from app.deps.tenant import tenant_dependency`
   - **Reason**: Enables tenant dependency usage

2. **`missing_baseservice_import`**
   - **Fix**: Add `from app.features.core.base_service import BaseService`
   - **Reason**: Enables BaseService inheritance

3. **`missing_tenant_parameter`**
   - **Fix**: Add `tenant_id: str` parameter to service `__init__`
   - **Reason**: Ensures service knows its tenant context

## Benefits

### 1. **Prevents Regression**
- Catches tenant isolation violations during development
- Ensures new code follows established patterns
- Prevents data leakage between tenants

### 2. **Enforces Standards**
- Automatic validation of standardized patterns
- Consistent transaction handling across services
- Proper dependency injection usage

### 3. **Documentation**
- Generates compliance reports for auditing
- Tracks compliance score over time
- Provides clear violation descriptions and fixes

### 4. **Developer Experience**
- Fast feedback during development
- Clear error messages with fix suggestions
- Integration with existing testing workflow
