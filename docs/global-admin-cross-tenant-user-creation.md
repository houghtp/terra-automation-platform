# Global Admin Cross-Tenant User Creation Implementation Guide

## Overview

This document provides a comprehensive guide for implementing cross-tenant user creation capabilities for global administrators in a FastAPI multi-tenant application. This feature allows global admins to create users and assign them to specific tenants, enabling proper tenant isolation and initial tenant setup.

## Table of Contents

- [Problem Statement](#problem-statement)
- [Solution Architecture](#solution-architecture)
- [Why This Implementation](#why-this-implementation)
- [Step-by-Step Implementation](#step-by-step-implementation)
- [Security Considerations](#security-considerations)
- [Testing Guide](#testing-guide)
- [Troubleshooting](#troubleshooting)

## Problem Statement

### The Challenge

In a multi-tenant FastAPI application, there's a chicken-and-egg problem:

1. **New tenants are created** by global administrators
2. **Tenants need users** to be functional
3. **Regular user creation** is tenant-scoped (users can only create users within their own tenant)
4. **Global admins** operate in the "global" tenant context
5. **No mechanism exists** for global admins to create the first user(s) for a new tenant

### Current Limitations

- Global admins can create tenants but cannot populate them with users
- Tenant admins cannot create the first user for their tenant (since they don't exist yet)
- Users created by global admins default to the "global" tenant
- No cross-tenant user assignment capability

## Solution Architecture

### Core Components

1. **Enhanced User Service**: Modified to accept optional `target_tenant_id` parameter
2. **Updated Routes**: Form endpoints that detect global admin status and provide tenant selection
3. **Conditional UI**: Tenant dropdown that appears only for global admins
4. **Validation Logic**: Ensures global admins must select a target tenant
5. **Security Enforcement**: Maintains tenant isolation for non-global admins

### Data Flow

```
Global Admin Login → User Creation Form → Tenant Selection → User Created in Target Tenant → Tenant User Can Login
```

### Security Model

- **Global Admins**: Can see all tenants and assign users to any tenant
- **Tenant Admins**: Cannot see tenant selection (field hidden), users auto-assigned to their tenant
- **Regular Users**: No user creation capabilities

## Why This Implementation

### Design Principles

1. **Least Privilege**: Tenant admins cannot create users outside their tenant
2. **Explicit Assignment**: Global admins must explicitly choose target tenant (no defaults)
3. **Backward Compatibility**: Existing tenant-scoped user creation unchanged
4. **Security First**: All tenant validation and isolation rules maintained
5. **User Experience**: Intuitive UI that shows/hides fields based on permissions

### Alternative Approaches Considered

| Approach | Pros | Cons | Why Not Used |
|----------|------|------|--------------|
| Separate Global User Creation Service | Clean separation | Code duplication | Violates DRY principle |
| Default Tenant Assignment | Simple implementation | Security risk | Could accidentally assign to wrong tenant |
| Manual POST-creation Assignment | Maintains existing code | Poor UX, error-prone | Creates operational overhead |
| Role-based Service Methods | Clean abstraction | Complex inheritance | Over-engineering for this use case |

## Step-by-Step Implementation

### Prerequisites

- Existing multi-tenant FastAPI application
- User management system with tenant isolation
- Global admin authentication system
- Tenant management system

### Step 1: Enhance User Service

**File**: `app/features/administration/users/services.py`

**Purpose**: Add cross-tenant user creation capability

**Changes**:

1. **Modify `create_user` method signature**:

```python
async def create_user(self, user_data: UserCreate, target_tenant_id: Optional[str] = None) -> UserResponse:
    """
    Create a new user with optional cross-tenant assignment for global admins.
    
    Args:
        user_data: User creation data
        target_tenant_id: Optional tenant ID for global admin cross-tenant creation
        
    Returns:
        UserResponse: Created user information
    """
```

2. **Add tenant resolution logic**:

```python
# Determine which tenant to create user in
effective_tenant_id = target_tenant_id or self.tenant_id
```

3. **Add cross-tenant email validation**:

```python
# Check if user with this email already exists in the target tenant
if target_tenant_id:
    # For cross-tenant creation, check the specific target tenant
    existing = await self._get_user_by_email_in_tenant(user_data.email, target_tenant_id)
else:
    # For normal operation, check current tenant
    existing = await self.get_user_by_email(user_data.email)
```

4. **Update user creation**:

```python
user = User(
    name=user_data.name,
    email=user_data.email,
    hashed_password=hash_password(user_data.password),
    description=user_data.description,
    status=user_data.status.value,
    role=user_data.role.value,
    enabled=user_data.enabled,
    tags=user_data.tags,
    tenant_id=effective_tenant_id  # KEY: Assign to target tenant
)
```

5. **Add helper method for cross-tenant email checking**:

```python
async def _get_user_by_email_in_tenant(self, email: str, tenant_id: str) -> Optional[User]:
    """Get user by email in a specific tenant (for global admin operations)."""
    stmt = select(User).where(
        and_(
            User.email == email,
            User.tenant_id == tenant_id,
            User.is_active == True
        )
    )
    result = await self.db.execute(stmt)
    return result.scalar_one_or_none()
```

6. **Add method to fetch available tenants**:

```python
async def get_available_tenants_for_user_forms(self) -> List[dict]:
    """Get available tenants for global admin user creation forms."""
    try:
        # Import here to avoid circular imports
        from app.features.administration.tenants.services import TenantManagementService
        from app.features.administration.tenants.schemas import TenantSearchFilter
        
        tenant_service = TenantManagementService(self.db)
        filters = TenantSearchFilter(status="active")  # Only active tenants
        tenants = await tenant_service.list_tenants(filters)
        
        return [{"id": tenant.id, "name": tenant.name} for tenant in tenants]
    except Exception as e:
        logger.error(f"Failed to get available tenants: {e}")
        return []
```

### Step 2: Update User Routes

**File**: `app/features/administration/users/routes.py`

**Purpose**: Handle global admin detection and tenant selection

**Changes**:

1. **Update form GET endpoints** to detect global admin status:

```python
@router.get("/partials/form", response_class=HTMLResponse)
async def user_form_partial(request: Request, user_id: str = None, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    user = None
    if user_id:
        service = UserManagementService(db, tenant)
        user = await service.get_user_by_id(user_id)

    # Check if current user is global admin
    is_global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"
    available_tenants = []

    if is_global_admin:
        # Get available tenants for global admin
        service = UserManagementService(db, tenant)
        available_tenants = await service.get_available_tenants_for_user_forms()

    return templates.TemplateResponse("administration/users/partials/form.html", {
        "request": request,
        "user": user,
        "is_global_admin": is_global_admin,
        "available_tenants": available_tenants
    })
```

2. **Update user creation POST endpoint**:

```python
@router.post("/")
async def user_create(request: Request, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Create a new user via form submission."""
    try:
        # ... existing form parsing code ...

        # Check if current user is global admin
        is_global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"
        target_tenant_id = None

        if is_global_admin:
            # For global admins, target_tenant_id is required
            target_tenant_id = form_handler.form_data.get("target_tenant_id")
            if not target_tenant_id:
                form_handler.errors.setdefault('target_tenant_id', []).append('Target tenant is required for global admin')

        # ... existing validation code ...

        # Create user with optional cross-tenant assignment
        service = UserManagementService(db, tenant)
        user = await service.create_user(user_data, target_tenant_id)
        await db.commit()

        # ... rest of the method ...
```

### Step 3: Update Form Template

**File**: `app/features/administration/users/templates/administration/users/partials/form.html`

**Purpose**: Add conditional tenant selection field

**Changes**:

Add tenant selection field that only appears for global admins creating new users:

```html
{# Tenant selection for global admins only #}
{% if is_global_admin and not user %}
<div class="col-md-6">
  <label class="form-label">Target Tenant *</label>
  <select
    name="target_tenant_id"
    required
    class="form-select {{ 'is-invalid' if errors and 'target_tenant_id' in errors else '' }}"
  >
    <option value="">Select a tenant...</option>
    {% for tenant in available_tenants %}
    <option value="{{ tenant.id }}" {{ 'selected' if form_data and form_data.target_tenant_id == tenant.id else '' }}>
      {{ tenant.name }}
    </option>
    {% endfor %}
  </select>
  {% if errors and 'target_tenant_id' in errors %}
    <div class="invalid-feedback">{{ errors.target_tenant_id[0] }}</div>
  {% endif %}
  <div class="form-text">
    Select which tenant this user will belong to.
  </div>
</div>
{% endif %}
```

**Key Points**:
- Field only shows for global admins (`is_global_admin`)
- Only shows when creating new users (`not user`)
- Field is required for global admins
- Displays validation errors
- Pre-selects previous value on form redisplay

### Step 4: Update Edit Form Endpoint

**File**: `app/features/administration/users/routes.py`

**Purpose**: Ensure edit forms also receive tenant data for global admins

```python
@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def user_edit_form(request: Request, user_id: str, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    service = UserManagementService(db, tenant)
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if current user is global admin
    is_global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"
    available_tenants = []

    if is_global_admin:
        # Get available tenants for global admin
        available_tenants = await service.get_available_tenants_for_user_forms()

    return templates.TemplateResponse("administration/users/partials/form.html", {
        "request": request,
        "user": user,
        "is_global_admin": is_global_admin,
        "available_tenants": available_tenants
    })
```

### Step 5: Error Handling Enhancement

**File**: `app/features/administration/users/routes.py`

**Purpose**: Ensure error responses include tenant data for form redisplay

**Changes**:

1. **In validation error handling**:

```python
if form_handler.has_errors():
    # Get tenant data for form redisplay
    available_tenants = []
    if is_global_admin:
        service = UserManagementService(db, tenant)
        available_tenants = await service.get_available_tenants_for_user_forms()

    # Return the form with error messages
    return templates.TemplateResponse("administration/users/partials/form.html", {
        "request": request,
        "user": None,
        "errors": form_handler.errors,
        "form_data": form_handler.form_data,
        "is_global_admin": is_global_admin,
        "available_tenants": available_tenants
    }, status_code=400)
```

2. **In service error handling**:

```python
except ValueError as e:
    # Get tenant data for form redisplay
    available_tenants = []
    is_global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"
    if is_global_admin:
        service = UserManagementService(db, tenant)
        available_tenants = await service.get_available_tenants_for_user_forms()

    # Return form with error
    return templates.TemplateResponse("administration/users/partials/form.html", {
        "request": request,
        "user": None,
        "errors": errors,
        "form_data": form_handler.form_data if 'form_handler' in locals() else {},
        "is_global_admin": is_global_admin,
        "available_tenants": available_tenants
    }, status_code=400)
```

## Security Considerations

### Access Control

1. **Global Admin Verification**: Always verify both role and tenant_id
   ```python
   is_global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"
   ```

2. **Tenant Validation**: Ensure target tenant exists and is active
3. **Email Uniqueness**: Check email uniqueness within target tenant, not globally
4. **Input Sanitization**: Validate all form inputs, especially tenant_id

### Tenant Isolation Enforcement

1. **Service Layer**: All database queries must include tenant filtering
2. **Route Layer**: Dependency injection ensures tenant context
3. **UI Layer**: Conditional rendering prevents information leakage
4. **Token Layer**: JWT tokens contain tenant_id for validation

### Audit and Logging

1. **User Creation Events**: Log all user creations with target tenant
2. **Global Admin Actions**: Special logging for cross-tenant operations
3. **Error Tracking**: Log validation failures and security violations
4. **Access Patterns**: Monitor for unusual cross-tenant access patterns

## Testing Guide

### Test Cases

#### 1. Global Admin User Creation

**Setup**: Login as global admin

**Test Steps**:
1. Navigate to user management
2. Click "Add User"
3. Verify tenant dropdown appears
4. Fill form with valid data
5. Select target tenant
6. Submit form
7. Verify user created in target tenant

**Expected Result**: User successfully created in selected tenant

#### 2. Tenant Admin User Creation

**Setup**: Login as tenant admin

**Test Steps**:
1. Navigate to user management
2. Click "Add User"
3. Verify tenant dropdown does NOT appear
4. Fill form with valid data
5. Submit form
6. Verify user created in admin's tenant

**Expected Result**: User created in tenant admin's own tenant

#### 3. Cross-Tenant Email Validation

**Setup**: 
- Existing user with email "test@example.com" in Tenant A
- Login as global admin

**Test Steps**:
1. Create new user with email "test@example.com" for Tenant B
2. Submit form

**Expected Result**: User created successfully (same email allowed in different tenants)

#### 4. Same-Tenant Email Validation

**Setup**: 
- Existing user with email "test@example.com" in Tenant A
- Login as global admin

**Test Steps**:
1. Create new user with email "test@example.com" for Tenant A
2. Submit form

**Expected Result**: Validation error - email already exists in tenant

#### 5. Required Field Validation

**Setup**: Login as global admin

**Test Steps**:
1. Click "Add User"
2. Fill form but leave target tenant empty
3. Submit form

**Expected Result**: Validation error - target tenant required

#### 6. Form Error Redisplay

**Setup**: Login as global admin

**Test Steps**:
1. Fill form with invalid data
2. Submit form
3. Verify form redisplays with:
   - Error messages
   - Previously entered values
   - Tenant dropdown still populated

**Expected Result**: Form maintains state and shows errors

### Test Data Setup

```sql
-- Create test tenants
INSERT INTO tenants (name, status, tier) VALUES 
('Test Tenant A', 'active', 'basic'),
('Test Tenant B', 'active', 'free');

-- Create global admin user
INSERT INTO users (name, email, hashed_password, role, tenant_id) VALUES 
('Global Admin', 'admin@system.local', 'hashed_password', 'global_admin', 'global');

-- Create tenant admin user
INSERT INTO users (name, email, hashed_password, role, tenant_id) VALUES 
('Tenant Admin', 'admin@tenanta.com', 'hashed_password', 'admin', '1');
```

### Automated Testing

```python
# Example test cases
async def test_global_admin_can_create_cross_tenant_user():
    # Setup global admin session
    # Create user for different tenant
    # Verify user created in target tenant
    pass

async def test_tenant_admin_cannot_see_tenant_dropdown():
    # Setup tenant admin session
    # Request user form
    # Verify no tenant selection field
    pass

async def test_cross_tenant_email_uniqueness():
    # Create user in tenant A
    # Create user with same email in tenant B
    # Verify both succeed
    pass
```

## Troubleshooting

### Common Issues

#### 1. Tenant Dropdown Not Appearing

**Symptoms**: Global admin doesn't see tenant selection field

**Causes**:
- User role is not "global_admin"
- User tenant_id is not "global"
- Template condition incorrect
- Frontend JavaScript errors

**Solutions**:
- Verify user role in database
- Check tenant_id value
- Review template conditional logic
- Check browser console for errors

#### 2. "Target tenant required" Error

**Symptoms**: Form validation fails even when tenant selected

**Causes**:
- Frontend not sending form data
- Backend not receiving target_tenant_id
- Form field name mismatch

**Solutions**:
- Check form field name attribute
- Verify form data in browser network tab
- Log form_data in backend route

#### 3. User Created in Wrong Tenant

**Symptoms**: User appears in different tenant than selected

**Causes**:
- target_tenant_id not passed to service
- Service logic error
- Database transaction issues

**Solutions**:
- Log effective_tenant_id in service
- Verify database queries
- Check transaction commit/rollback

#### 4. Available Tenants Not Loading

**Symptoms**: Tenant dropdown is empty

**Causes**:
- Tenant service errors
- Database connection issues
- Circular import problems

**Solutions**:
- Check application logs
- Verify tenant service functionality
- Review import statements

### Debug Checklist

1. **Authentication**:
   - [ ] User authenticated correctly
   - [ ] Global admin role verified
   - [ ] Tenant context set properly

2. **Form Rendering**:
   - [ ] `is_global_admin` flag correct
   - [ ] `available_tenants` populated
   - [ ] Template condition working

3. **Form Submission**:
   - [ ] Form data received
   - [ ] `target_tenant_id` extracted
   - [ ] Validation logic working

4. **Service Layer**:
   - [ ] `target_tenant_id` passed correctly
   - [ ] `effective_tenant_id` calculated
   - [ ] User created with correct tenant

5. **Database**:
   - [ ] User record has correct tenant_id
   - [ ] Transaction committed
   - [ ] No constraint violations

### Logging Strategy

```python
# Add strategic logging points
logger.info(f"Global admin status: {is_global_admin}")
logger.info(f"Available tenants: {len(available_tenants)}")
logger.info(f"Target tenant: {target_tenant_id}")
logger.info(f"Effective tenant: {effective_tenant_id}")
logger.info(f"User created in tenant: {user.tenant_id}")
```

## Conclusion

This implementation provides a secure, user-friendly solution for global administrators to create users across tenants while maintaining strict tenant isolation for regular users. The approach balances security, usability, and maintainability while following established patterns in the codebase.

### Key Benefits

1. **Security**: Maintains tenant isolation and prevents unauthorized access
2. **Usability**: Intuitive interface that adapts to user permissions
3. **Maintainability**: Minimal code changes with clear separation of concerns
4. **Scalability**: Handles multiple tenants efficiently
5. **Backward Compatibility**: Existing functionality unchanged

### Future Enhancements

1. **Bulk User Creation**: Import users from CSV with tenant assignment
2. **User Migration**: Move users between tenants
3. **Tenant Templates**: Create users with predefined roles per tenant type
4. **Audit Dashboard**: Track cross-tenant user creation activities
5. **API Endpoints**: Provide REST API for programmatic user creation

This guide provides everything needed to implement robust cross-tenant user creation capabilities in your FastAPI multi-tenant application.
