
# Automated Tenant CRUD Compliance Report

## Summary
- **Total Files Checked**: 23
  - Route Files: 13
  - Service Files: 10
- **Compliance Score**: 82.6%
- **Status**: WARNING
- **Violations Found**: 4

## Violations by Type

### Missing Baseservice Import (2 violations)
- `/home/paul/repos/terra-automation-platform/app/features/administration/tenants/services.py:23` - File should import BaseService from app.features.core.base_service
- `/home/paul/repos/terra-automation-platform/app/features/auth/services.py:13` - File should import BaseService from app.features.core.base_service

### Missing Tenant Parameter (2 violations)
- `/home/paul/repos/terra-automation-platform/app/features/administration/tenants/services.py:37` - Service __init__ should accept tenant_id parameter for proper isolation
- `/home/paul/repos/terra-automation-platform/app/features/auth/services.py:16` - Service __init__ should accept tenant_id parameter for proper isolation
