# Global Admin System

The TerraAutomationPlatform includes a comprehensive global administrator system for managing multi-tenant applications.

## Overview

The global admin system provides:
- **Bootstrap mechanism** - Automatically creates initial admin account
- **Tenant management** - Only global admins can create/manage tenants  
- **System-level access** - Special privileges for system administration
- **Security isolation** - Global admins use special tenant_id "global"

## Key Concepts

### Roles Hierarchy
- **`user`** - Regular tenant users
- **`admin`** - Tenant administrators (manage users within their tenant)
- **`global_admin`** - Global administrators (manage tenants and system)

### Special Tenant
- Global admins use `tenant_id: "global"`
- This isolates system-level operations from tenant data
- Global admins cannot access tenant-specific data directly

## Setup & Bootstrap

### Automatic Bootstrap
On application startup, the system automatically:
1. Checks if any global admin exists
2. Creates default admin if none found
3. Logs the credentials for first-time setup

### Environment Variables
```bash
# Global admin configuration
GLOBAL_ADMIN_EMAIL=admin@yourdomain.com
GLOBAL_ADMIN_PASSWORD=your-secure-password
GLOBAL_ADMIN_NAME="System Administrator"
```

### Manual Management
Use the CLI tool for global admin management:

```bash
# Bootstrap default admin
python manage_global_admin.py bootstrap

# Create new global admin interactively
python manage_global_admin.py create

# List all global admins  
python manage_global_admin.py list

# Validate system setup
python manage_global_admin.py validate

# Show help
python manage_global_admin.py help
```

## API Usage

### Authentication
Global admins authenticate normally but receive special permissions:

```python
# Login as global admin
POST /auth/login
{
    "email": "admin@system.local",
    "password": "your-password"
}
```

### Tenant Management
Only global admins can manage tenants:

```python
# Create tenant (requires global_admin role)
POST /tenants/
{
    "name": "customer-tenant",
    "metadata": {"tier": "premium"}
}

# List all tenants (requires global_admin role)
GET /tenants/

# Delete tenant (requires global_admin role)  
DELETE /tenants/{tenant_id}
```

## Security Features

### Role-Based Access Control
The system provides three dependency functions:

```python
from app.auth.dependencies import (
    get_admin_user,          # admin OR global_admin
    get_global_admin_user,   # global_admin only
    get_tenant_admin_user    # admin only (excludes global_admin)
)

# Protect endpoint for global admins only
@router.post("/system/config")
async def update_system_config(
    config: SystemConfig,
    admin: User = Depends(get_global_admin_user)
):
    # Only global admins can access this
    pass
```

### Tenant Isolation
- Global admins cannot access tenant data through normal endpoints
- Tenant admins cannot access system-level functions
- Each tenant's data is completely isolated

### Bootstrap Security
- Auto-generates secure password if none provided
- Warns about default credentials
- Requires manual password change for production

## Production Deployment

### 1. Set Environment Variables
```bash
# Required for production
export GLOBAL_ADMIN_EMAIL=admin@yourdomain.com
export GLOBAL_ADMIN_PASSWORD=your-very-secure-password
export GLOBAL_ADMIN_NAME="Your System Admin"
```

### 2. Validate Setup
```bash
# Check system health
python manage_global_admin.py validate
```

### 3. Create Additional Admins
```bash
# Create backup admin
python manage_global_admin.py create
```

### 4. Change Default Credentials
- Never use default email `admin@system.local` in production
- Use strong passwords (16+ characters)
- Consider using secrets management for credentials

## Integration Examples

### Protect System Routes
```python
@router.post("/system/maintenance")
async def enable_maintenance_mode(
    enabled: bool,
    admin: User = Depends(get_global_admin_user)
):
    \"\"\"Only global admins can toggle maintenance mode.\"\"\"
    # Implementation here
    pass
```

### Multi-Level Admin Check
```python
@router.get("/admin/dashboard")
async def admin_dashboard(
    admin: User = Depends(get_admin_user)  # admin OR global_admin
):
    if admin.role == "global_admin":
        # Show system-wide statistics
        return await get_system_stats()
    else:
        # Show tenant-specific statistics  
        return await get_tenant_stats(admin.tenant_id)
```

### Tenant Creation Workflow
```python
@router.post("/onboard-customer")
async def onboard_new_customer(
    customer_data: CustomerData,
    global_admin: User = Depends(get_global_admin_user)
):
    # 1. Create tenant
    tenant = await create_tenant(customer_data.company_name)
    
    # 2. Create tenant admin user
    tenant_admin = await create_user(
        email=customer_data.admin_email,
        tenant_id=str(tenant.id),
        role="admin"
    )
    
    # 3. Send welcome email
    await send_welcome_email(tenant_admin)
    
    return {"tenant_id": tenant.id, "admin_id": tenant_admin.id}
```

## Troubleshooting

### No Global Admin Found
```bash
# Bootstrap will create one automatically
python manage_global_admin.py bootstrap
```

### Multiple Global Admins
This is normal and recommended for redundancy.

### Locked Out of System
1. Check database directly for global admins
2. Use environment variables to reset password
3. Bootstrap new admin if necessary

### Permission Denied
Ensure the user has `role: "global_admin"` and `tenant_id: "global"`

## Best Practices

1. **Always have backup global admin** - Don't rely on single account
2. **Use strong passwords** - 16+ characters with mixed types
3. **Regular password rotation** - Change passwords periodically
4. **Monitor admin actions** - Audit all global admin activities
5. **Separate concerns** - Don't use global admin for tenant operations
6. **Environment-specific configs** - Different admins for dev/staging/prod

## Database Schema

Global admins are stored in the same `users` table with special values:
```sql
SELECT * FROM users WHERE tenant_id = 'global' AND role = 'global_admin';
```

The system automatically creates these during bootstrap or manual creation.

## API Reference

See the full API documentation at `/docs` when running the application. Global admin endpoints are tagged with `[tenants]` and require global admin authentication.

## Security Audit

The global admin system has been designed with security as the top priority:
- ✅ Proper role-based access control
- ✅ Tenant isolation maintained
- ✅ Secure password handling
- ✅ Audit logging for all actions
- ✅ Bootstrap safety mechanisms
- ✅ Production-ready defaults

Regular security reviews ensure the system remains secure and up-to-date with best practices.