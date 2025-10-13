# 🔍 Audit Field Standardization - Background Task

## 📋 Task Overview
Audit all service files that create or update database records to ensure proper handling of AuditMixin fields (`created_at`, `updated_at`, `created_by_*`, etc.). Fix any missing imports, incorrect timestamp handling, or incomplete audit field population.

---

## 🎯 Objectives

1. **Verify IntegrityError Import**: Ensure all CRUD services that catch database errors import `IntegrityError`
2. **Verify Audit Timestamp Handling**: Ensure all create/update operations explicitly set `created_at` and `updated_at`
3. **Verify Audit Context Usage**: Ensure all operations use `AuditContext.from_user()` correctly
4. **Standardize Error Handling**: Ensure consistent exception handling patterns
5. **Check Lazy Loading Issues**: Verify no `user.attribute` accesses that could trigger lazy loads after session closes

---

## 🔍 Search Patterns

### 1. Find All CRUD Services
```bash
find app/features -name "crud_services.py" -o -name "*_service.py" | grep -v __pycache__
```

### 2. Find Services That Create Records
```bash
grep -r "async def create_" app/features --include="*service*.py" -l
```

### 3. Find Services That Update Records
```bash
grep -r "async def update_" app/features --include="*service*.py" -l
```

### 4. Find IntegrityError Catches Without Import
```bash
# Find files catching IntegrityError
grep -r "except IntegrityError" app/features --include="*.py" -l > /tmp/integrity_files.txt

# Check each file for the import
while read file; do
    if ! grep -q "from sqlalchemy.exc import IntegrityError" "$file"; then
        echo "MISSING IMPORT: $file"
    fi
done < /tmp/integrity_files.txt
```

### 5. Find AuditMixin Usage Without Explicit Timestamps
```bash
# Find models using AuditMixin
grep -r "class.*AuditMixin" app/features --include="*.py" -B 1

# Find create operations that might not set timestamps
grep -r "\.set_created_by\(" app/features --include="*service*.py" -A 2 | grep -v "created_at"
```

---

## ✅ Standard Patterns to Follow

### **Pattern 1: Correct Imports**
```python
"""
Service description
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService
from sqlalchemy.exc import IntegrityError  # ✅ REQUIRED for exception handling
from datetime import datetime  # ✅ REQUIRED for explicit timestamps

from app.features.core.audit_mixin import AuditContext

logger = get_logger(__name__)
```

### **Pattern 2: Correct Create Operation**
```python
async def create_entity(
    self,
    entity_data: EntityCreate,
    created_by_user: User,
    target_tenant_id: Optional[str] = None
) -> EntityResponse:
    """Create a new entity."""
    try:
        effective_tenant_id = target_tenant_id or self.tenant_id

        # Create audit context
        audit_ctx = AuditContext.from_user(created_by_user)

        # Create the entity record
        entity = Entity(
            tenant_id=effective_tenant_id,
            name=entity_data.name,
            description=entity_data.description,
            # ... other fields
        )

        # ✅ CRITICAL: Set audit information with explicit timestamps
        entity.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
        entity.created_at = datetime.now()
        entity.updated_at = datetime.now()

        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)

        logger.info(f"Created entity '{entity_data.name}' for tenant {effective_tenant_id}")
        return EntityResponse.model_validate(entity)

    except IntegrityError as e:
        await self.db.rollback()
        error_str = str(e)
        logger.error(f"Failed to create entity - IntegrityError", error=error_str)

        if "unique constraint" in error_str.lower():
            raise ValueError(f"Entity with name '{entity_data.name}' already exists")
        else:
            raise ValueError(f"Database constraint violation: {error_str}")

    except Exception as e:
        await self.db.rollback()
        logger.exception("Failed to create entity")
        raise ValueError(f"Failed to create entity: {str(e)}")
```

### **Pattern 3: Correct Update Operation**
```python
async def update_entity(
    self,
    entity_id: int,
    update_data: EntityUpdate,
    updated_by_user: User
) -> Optional[EntityResponse]:
    """Update an entity."""
    try:
        entity = await self.get_entity_by_id(entity_id)
        if not entity:
            return None

        # Create audit context
        audit_ctx = AuditContext.from_user(updated_by_user)

        # Update fields (only if provided)
        if update_data.name is not None:
            entity.name = update_data.name
        if update_data.description is not None:
            entity.description = update_data.description
        # ... other fields

        # ✅ CRITICAL: Set audit information with explicit timestamp
        entity.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
        entity.updated_at = datetime.now()

        await self.db.flush()
        await self.db.refresh(entity)

        logger.info(f"Updated entity {entity_id}")
        return EntityResponse.model_validate(entity)

    except IntegrityError as e:
        await self.db.rollback()
        error_str = str(e)
        logger.error(f"Failed to update entity - IntegrityError", error=error_str)
        raise ValueError(f"Database constraint violation: {error_str}")

    except Exception as e:
        await self.db.rollback()
        logger.exception(f"Failed to update entity {entity_id}")
        raise ValueError(f"Failed to update entity: {str(e)}")
```

### **Pattern 4: Correct Delete Operation**
```python
async def delete_entity(
    self,
    entity_id: int,
    deleted_by_user: User
) -> bool:
    """Soft delete an entity."""
    try:
        entity = await self.get_entity_by_id(entity_id)
        if not entity:
            return False

        # Create audit context
        audit_ctx = AuditContext.from_user(deleted_by_user)

        # ✅ CRITICAL: Set deletion audit information
        entity.set_deleted_by(audit_ctx.user_email, audit_ctx.user_name)
        entity.deleted_at = datetime.now()

        await self.db.flush()

        logger.info(f"Deleted entity {entity_id}")
        return True

    except Exception as e:
        await self.db.rollback()
        logger.exception(f"Failed to delete entity {entity_id}")
        return False
```

### **Pattern 5: Safe User Attribute Access (Routes)**
```python
def is_global_admin(user: User) -> bool:
    """
    Check if user is global admin.
    Uses __dict__ to avoid lazy-loading when session is closed.
    """
    try:
        # ✅ CRITICAL: Access from __dict__ to avoid lazy loading
        user_dict = user.__dict__
        return user_dict.get("role") == "global_admin" and user_dict.get("tenant_id") == "global"
    except Exception:
        return False

# ❌ WRONG: Direct attribute access can trigger lazy loads
# return user.role == "global_admin" and user.tenant_id == "global"
```

---

## 🔧 Files to Audit (Priority Order)

### **High Priority - User-Facing CRUD Services**
1. ✅ `app/features/administration/secrets/services/crud_services.py` - **ALREADY FIXED**
2. `app/features/administration/users/services/crud_services.py`
3. `app/features/administration/tenants/services/crud_services.py`
4. `app/features/administration/audit/services/crud_services.py`
5. `app/features/administration/api_keys/services/crud_services.py`
6. `app/features/administration/smtp/services/crud_services.py`
7. `app/features/administration/tasks/services/task_service.py`

### **Medium Priority - Business Automation Services**
8. `app/features/business_automations/content_broadcaster/services/content_planning_service.py`
9. `app/features/business_automations/content_broadcaster/services/content_item_service.py`
10. `app/features/connectors/connectors/services/connector_service.py`

### **Lower Priority - Monitoring Services**
11. `app/features/monitoring/logs/services/log_service.py`
12. `app/features/monitoring/metrics/services/metrics_service.py`

---

## 📝 Checklist for Each Service File

For each service file, verify:

- [ ] **Import Check**: Has `from sqlalchemy.exc import IntegrityError`
- [ ] **Import Check**: Has `from datetime import datetime`
- [ ] **Import Check**: Has `from app.features.core.audit_mixin import AuditContext`
- [ ] **Create Methods**: Call `entity.set_created_by(audit_ctx.user_email, audit_ctx.user_name)`
- [ ] **Create Methods**: Set `entity.created_at = datetime.now()`
- [ ] **Create Methods**: Set `entity.updated_at = datetime.now()`
- [ ] **Update Methods**: Call `entity.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)`
- [ ] **Update Methods**: Set `entity.updated_at = datetime.now()`
- [ ] **Delete Methods**: Call `entity.set_deleted_by(audit_ctx.user_email, audit_ctx.user_name)`
- [ ] **Delete Methods**: Set `entity.deleted_at = datetime.now()`
- [ ] **Error Handling**: All `except IntegrityError` blocks have the import
- [ ] **Error Handling**: Consistent error logging with `logger.error()` or `logger.exception()`
- [ ] **Transaction Management**: `await self.db.rollback()` in exception handlers

---

## 🚨 Common Issues to Fix

### **Issue 1: Missing IntegrityError Import**
```python
# ❌ WRONG - Will cause NameError
except IntegrityError as e:
    pass

# ✅ CORRECT - Add import at top of file
from sqlalchemy.exc import IntegrityError
```

### **Issue 2: Missing Explicit Timestamps**
```python
# ❌ WRONG - Relies on server_default which doesn't always work with async
entity.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
self.db.add(entity)

# ✅ CORRECT - Explicitly set timestamps
entity.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
entity.created_at = datetime.now()
entity.updated_at = datetime.now()
self.db.add(entity)
```

### **Issue 3: Lazy Loading User Attributes**
```python
# ❌ WRONG - Can trigger lazy load after session closes
if user.role == "global_admin":
    pass

# ✅ CORRECT - Use __dict__ to avoid descriptor
user_dict = user.__dict__
if user_dict.get("role") == "global_admin":
    pass
```

### **Issue 4: Inconsistent Error Handling**
```python
# ❌ WRONG - Swallows exceptions, no logging
except Exception:
    pass

# ✅ CORRECT - Log with context, re-raise appropriately
except IntegrityError as e:
    await self.db.rollback()
    logger.error(f"Database integrity error", error=str(e))
    raise ValueError("Duplicate record or constraint violation")
except Exception as e:
    await self.db.rollback()
    logger.exception("Unexpected error during operation")
    raise ValueError(f"Operation failed: {str(e)}")
```

---

## 🧪 Testing Strategy

After fixing each service:

1. **Test Create**: Try creating a new record
   - Verify no `NotNullViolationError` for `created_at`
   - Verify audit fields are populated in database

2. **Test Update**: Try updating an existing record
   - Verify `updated_at` is set
   - Verify `updated_by_*` fields are populated

3. **Test Delete**: Try soft-deleting a record
   - Verify `deleted_at` is set
   - Verify `deleted_by_*` fields are populated

4. **Test Error Cases**: Try duplicate inserts, invalid data
   - Verify `IntegrityError` is caught and handled
   - Verify appropriate error messages returned
   - Verify no `NameError` exceptions

---

## 📊 Report Format

For each file audited, create a summary:

```markdown
### File: app/features/[module]/services/[service].py

**Status**: ✅ Fixed | ⚠️ Needs Review | ❌ Has Issues

**Issues Found**:
- [ ] Missing IntegrityError import
- [ ] Missing datetime import
- [ ] Missing explicit created_at in create methods
- [ ] Missing explicit updated_at in update methods
- [ ] Lazy loading risk in user attribute access
- [ ] Inconsistent error handling

**Changes Made**:
- Added `from sqlalchemy.exc import IntegrityError`
- Added explicit `entity.created_at = datetime.now()` in create_entity()
- Added explicit `entity.updated_at = datetime.now()` in update_entity()
- Improved error logging in exception handlers

**Testing**: ✅ Create | ✅ Update | ✅ Delete | ✅ Error Cases
```

---

## 🎯 Success Criteria

Task is complete when:

1. ✅ All CRUD services have correct imports
2. ✅ All create operations set audit timestamps explicitly
3. ✅ All update operations set updated_at explicitly
4. ✅ All delete operations set deleted_at explicitly
5. ✅ No NameError exceptions for IntegrityError
6. ✅ No NotNullViolationError for created_at/updated_at
7. ✅ Consistent error handling across all services
8. ✅ All tests pass (create, update, delete, error cases)

---

## 📚 Reference Files

**Already Fixed (Use as Examples)**:
- ✅ `app/features/administration/secrets/services/crud_services.py`
- ✅ `app/features/administration/secrets/routes/crud_routes.py`
- ✅ `app/features/core/route_imports.py` (is_global_admin helper)

**Standard Patterns**:
- 📖 `app/features/core/audit_mixin.py` - AuditMixin and AuditContext definitions
- 📖 `docs/fastapi-sqlalchemy-standards.md` - Overall standards documentation
- 📖 `.github/instructions/instructions.instructions.md` - Project conventions

---

## 🚀 Execution Steps

1. **Phase 1: Discovery**
   - Run search patterns to find all files needing audit
   - Create list of files with issues
   - Prioritize by user impact

2. **Phase 2: Fix High Priority**
   - Fix all user-facing CRUD services first
   - Test each fix individually
   - Commit after each working fix

3. **Phase 3: Fix Medium Priority**
   - Fix business automation services
   - Test integrations
   - Commit after validation

4. **Phase 4: Fix Lower Priority**
   - Fix monitoring and background services
   - Complete testing
   - Final commit

5. **Phase 5: Documentation**
   - Update standards documentation
   - Create final audit report
   - Document any exceptions or special cases

---

## ⚠️ Important Notes

1. **DO NOT** modify files in `app/features/core/` without review - these are shared utilities
2. **DO** test each fix individually before moving to next file
3. **DO** preserve existing business logic - only fix audit field handling
4. **DO** keep error messages consistent with existing patterns
5. **DO** commit frequently with clear messages: "fix: Add explicit audit timestamps to [module] service"

---

## 📞 Questions or Issues?

If you encounter:
- Complex service patterns not covered here
- Services that don't use AuditMixin
- Third-party models that can't be modified
- Migration-related issues

Document the issue and flag for review rather than making assumptions.

---

**End of Task Specification**
