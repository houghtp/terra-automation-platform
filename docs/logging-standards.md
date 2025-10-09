# 📝 Logging Standards & Best Practices

## Overview

This document defines the standardized logging practices for the TerraAutomationPlatform to ensure consistency, debuggability, and maintainability across the entire codebase.

## 🎯 Core Standards

### 1. **Use Structlog Exclusively**
- ✅ **DO**: `import structlog`
- ❌ **DON'T**: `import logging` (except in core logging infrastructure)

### 2. **Logger Initialization**
```python
# ✅ Correct Pattern
import structlog
logger = structlog.get_logger(__name__)

# ❌ Incorrect Patterns
import logging
logger = logging.getLogger(__name__)
logger = logging.getLogger()
```

### 3. **Structured Logging with Context**
```python
# ✅ Correct - Structured with context
logger.info("User created successfully",
           user_id=user.id,
           tenant_id=tenant_id,
           email=user.email)

# ❌ Incorrect - String formatting
logger.info(f"User {user.id} created for tenant {tenant_id}")
```

### 4. **Error Logging with Exception Details**
```python
# ✅ Correct - Exception with context
try:
    result = await service.create_user(data)
except ValidationError as e:
    logger.error("User validation failed",
                error=str(e),
                user_data=data.dict(),
                tenant_id=tenant_id,
                exc_info=True)
    raise

# ❌ Incorrect - String-based error logging
except ValidationError as e:
    logger.error(f"Failed to create user: {e}")
```

## 📋 Compliance Requirements

### Services Layer
- Must use `structlog.get_logger(__name__)`
- All database operations must log with tenant context
- Exception handling must include structured error details
- Performance-sensitive operations should use debug level

### Routes Layer
- Must include request ID in log context
- Must log tenant context for multi-tenant endpoints
- API errors must be logged with structured details
- Authentication failures must be logged with security context

### Core Infrastructure
- May use standard logging for bootstrap/configuration
- Must provide structured logging setup for application layers
- Should not expose standard logging to business logic layers

## 🔍 Log Levels

- **DEBUG**: Development debugging, verbose operation details
- **INFO**: Normal operation flow, business events
- **WARNING**: Recoverable issues, deprecated usage
- **ERROR**: Application errors, exception handling
- **CRITICAL**: System failures, security incidents

## 🏗️ Context Standards

### Required Context Fields
- **tenant_id**: For all multi-tenant operations
- **user_id**: For user-specific operations
- **request_id**: For API request tracing
- **operation**: Business operation being performed

### Optional Context Fields
- **performance_ms**: For timing-sensitive operations
- **resource_id**: For resource-specific operations
- **batch_id**: For batch processing operations

## 🚨 Security Considerations

### Never Log Sensitive Data
- ❌ Passwords, tokens, API keys
- ❌ PII without explicit consent
- ❌ Raw SQL queries with parameters
- ❌ Full request/response bodies

### Safe Logging Patterns
```python
# ✅ Safe - Log operation without sensitive data
logger.info("Secret created", secret_name=secret.name, tenant_id=tenant_id)

# ❌ Unsafe - Logs secret value
logger.info("Secret created", secret_data=secret.value)
```

## 🔧 Implementation Examples

### Service Layer
```python
import structlog
from app.features.core.base_service import BaseService

logger = structlog.get_logger(__name__)

class UserService(BaseService):
    async def create_user(self, user_data: UserCreate) -> User:
        try:
            logger.info("Creating user",
                       email=user_data.email,
                       tenant_id=self.tenant_id)

            user = await self._create_user_record(user_data)

            logger.info("User created successfully",
                       user_id=user.id,
                       tenant_id=self.tenant_id,
                       email=user.email)
            return user

        except IntegrityError as e:
            logger.error("User creation failed - constraint violation",
                        error=str(e),
                        email=user_data.email,
                        tenant_id=self.tenant_id,
                        exc_info=True)
            raise ValueError("User already exists")
```

### Route Layer
```python
import structlog
from fastapi import APIRouter, Depends, Request

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.post("/users")
async def create_user(
    request: Request,
    user_data: UserCreate,
    tenant_id: str = Depends(tenant_dependency)
):
    request_id = request.headers.get("x-request-id", "unknown")

    logger.info("API: Create user request",
               request_id=request_id,
               tenant_id=tenant_id,
               endpoint="/users")

    try:
        service = UserService(db, tenant_id)
        user = await service.create_user(user_data)

        logger.info("API: User created successfully",
                   request_id=request_id,
                   user_id=user.id,
                   tenant_id=tenant_id)

        return user

    except ValueError as e:
        logger.warning("API: User creation validation failed",
                      request_id=request_id,
                      error=str(e),
                      tenant_id=tenant_id)
        raise HTTPException(status_code=400, detail=str(e))
```

## 🔄 Migration Guide

### Step 1: Update Imports
```python
# Before
import logging
logger = logging.getLogger(__name__)

# After
import structlog
logger = structlog.get_logger(__name__)
```

### Step 2: Convert Log Calls
```python
# Before
logger.error(f"Failed to create user {user_id}: {error}")

# After
logger.error("User creation failed",
            user_id=user_id,
            error=str(error),
            exc_info=True)
```

### Step 3: Add Context
```python
# Before
logger.info("User created")

# After
logger.info("User created",
           user_id=user.id,
           tenant_id=tenant_id,
           operation="user_creation")
```

## 📊 Compliance Metrics

The logging compliance checker validates:
- ✅ Structlog usage (vs standard logging)
- ✅ Proper logger initialization patterns
- ✅ Structured logging with context fields
- ✅ Exception logging best practices
- ✅ Security-safe logging (no sensitive data)

**Target Compliance**: 95%+ across all application code
**Current Status**: ~25% (16/63 files)
**Priority**: High - Essential for debugging and monitoring

---

This document serves as the foundation for automated compliance checking and manual code reviews.
