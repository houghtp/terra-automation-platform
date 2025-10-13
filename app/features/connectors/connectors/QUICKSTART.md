# Connectors Slice - Quick Start Guide

## 5-Minute Setup

### 0. Install Dependencies (First Time Only)
```bash
# Install all dependencies including jsonschema
pip install -r requirements.txt

# Or install just the connector dependency
pip install jsonschema>=4.17.0
```

### 1. Ensure Database is Migrated
```bash
# Check current migration status
python3 manage_db.py current

# Should show: f88baf2363d9 (Update connector tables to match PRP specification)
# If not, run:
python3 manage_db.py upgrade
```

### 2. Seed the Connector Catalog
```bash
python3 app/seed_connectors.py
```

Expected output:
```
✅ Connector catalog seeding successful!
4 created, 0 updated, 0 skipped
```

### 3. Start the Server
```bash
uvicorn app.main:app --reload
```

### 4. Access the UI
1. Navigate to: `http://localhost:8000/auth/login`
2. Log in with your credentials
3. Navigate to: `http://localhost:8000/features/connectors/`

## Using the Connectors UI

### Browsing the Catalog
- Click the **"Catalog"** tab
- View available connector types with icons and descriptions
- See capabilities (e.g., "280 character limit" for Twitter)

### Installing a Connector
1. Click **"Add Connector"** on any catalog card
2. Fill in the form:
   - **Name**: A label for this instance (e.g., "Marketing Twitter")
   - **Config fields**: Connector-specific settings (dynamically generated)
   - **Auth fields**: Credentials (will be encrypted)
3. Click **"Create Connector"**
4. Success toast appears, card added to Installed tab

### Managing Installed Connectors
- Click the **"Installed"** tab
- See all your configured connectors
- Each card shows:
  - Status badge (Inactive/Active/Error)
  - Connector name and type
  - Auth status (configured or not)
  - Tags

**Actions:**
- **Configure**: Edit settings and credentials
- **Activate/Deactivate**: Toggle connector status
- **Delete**: Remove connector instance

## API Usage Examples

### List Available Connectors (Catalog)
```bash
curl http://localhost:8000/features/connectors/api/catalog \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response:
```json
[
  {
    "id": "uuid",
    "key": "twitter",
    "name": "Twitter (X)",
    "category": "Social",
    "auth_type": "oauth",
    "capabilities": {
      "post_text": true,
      "post_images": true,
      "max_length": 280
    },
    "default_config_schema": {
      "type": "object",
      "required": ["account_label"],
      "properties": { ... }
    }
  },
  ...
]
```

### List Installed Connectors
```bash
curl http://localhost:8000/features/connectors/api/installed \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response:
```json
[
  {
    "id": "uuid",
    "tenant_id": "tenant-123",
    "name": "Marketing Twitter",
    "status": "active",
    "config": {"account_label": "@marketing"},
    "auth_configured": true,  // Note: actual auth never exposed
    "catalog_key": "twitter",
    "catalog_name": "Twitter (X)",
    "created_at": "2025-10-10T12:00:00Z"
  }
]
```

### Install a Connector
```bash
curl -X POST http://localhost:8000/features/connectors/api/connectors \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "catalog_id": "CATALOG_UUID",
    "name": "My Twitter Account",
    "config": {
      "account_label": "@myhandle"
    },
    "auth": {
      "api_key": "your-api-key",
      "api_secret": "your-api-secret",
      "access_token": "your-access-token",
      "access_token_secret": "your-token-secret"
    },
    "tags": ["social", "marketing"]
  }'
```

**Important**: Auth credentials are encrypted before storage and never returned in responses.

### Update a Connector
```bash
curl -X PUT http://localhost:8000/features/connectors/api/connectors/CONNECTOR_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "status": "active",
    "config": {
      "account_label": "@newhandle"
    }
  }'
```

**Note**: To update auth, include the `auth` object with new credentials.

### Delete a Connector
```bash
curl -X DELETE http://localhost:8000/features/connectors/api/connectors/CONNECTOR_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Validate Configuration
```bash
curl -X POST http://localhost:8000/features/connectors/api/validate-config \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "catalog_key": "twitter",
    "config": {
      "account_label": "@test"
    }
  }'
```

Response:
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

### Get Publish Targets
```bash
curl http://localhost:8000/features/connectors/api/publish-targets \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response:
```json
[
  {
    "id": "uuid",
    "name": "Marketing Twitter",
    "connector_type": "twitter",
    "icon": "brand-x"
  }
]
```

**Use case**: Content Broadcaster can call this to get list of active connectors to publish to.

## Integration with Content Broadcaster

The Content Broadcaster feature uses the Connectors API to get available publish targets:

```python
from app.features.connectors.connectors.services.connector_service import connector_service

# Get active connectors for publishing
targets = await connector_service.get_publish_targets(tenant_id)

# Returns only active connectors with decrypted auth
for target in targets:
    # Use target['name'], target['connector_type'], target['auth']
    await publish_to_connector(target, content)
```

## Adding a New Connector Type

### 1. Add to Seed Data
Edit `app/seed_connectors.py`:

```python
{
    "key": "instagram",
    "name": "Instagram",
    "description": "Post photos and stories to Instagram",
    "category": "Social",
    "icon": "brand-instagram",
    "auth_type": AuthType.OAUTH.value,
    "capabilities": {
        "post_images": True,
        "post_videos": True,
        "post_stories": True,
        "max_image_size_mb": 8
    },
    "default_config_schema": {
        "type": "object",
        "required": ["account_id"],
        "properties": {
            "account_id": {
                "type": "string",
                "title": "Instagram Account ID",
                "description": "Your Instagram Business Account ID"
            }
        }
    }
}
```

### 2. Run Seeding
```bash
python3 app/seed_connectors.py
```

The script will automatically add new connectors and update existing ones.

### 3. Implement Publishing Logic
In Content Broadcaster or wherever you use connectors:

```python
async def publish_to_instagram(connector: dict, content: dict):
    # connector['auth'] contains decrypted credentials
    # connector['config'] contains account_id and other settings

    auth = connector['auth']
    config = connector['config']

    # Use Instagram API to publish
    # ...
```

## Security Notes

### Auth Encryption
- All `auth` data is encrypted using Fernet symmetric encryption
- Encryption key: `CONNECTOR_AUTH_ENCRYPTION_KEY` environment variable
- Auth credentials are NEVER returned in API responses
- Only `auth_configured: bool` is exposed

### Tenant Isolation
- All installed connectors are scoped to tenant_id
- Users can only see/modify connectors in their tenant
- Catalog is global (read-only)

### RBAC
- Read operations: Any authenticated user
- Write operations: Tenant admin or owner only

## Troubleshooting

### Migration Fails
```bash
# Check current migration
python3 manage_db.py current

# Check migration history
python3 manage_db.py history

# If stuck, ensure old connector tables are dropped
python3 -c "
import asyncio
from sqlalchemy import text
from app.features.core.database import engine

async def drop_old():
    async with engine.begin() as conn:
        await conn.execute(text('DROP TABLE IF EXISTS tenant_connectors CASCADE'))
        await conn.execute(text('DROP TABLE IF EXISTS available_connectors CASCADE'))
        await conn.execute(text('DROP TABLE IF EXISTS connectors_configurations CASCADE'))

asyncio.run(drop_old())
"

# Then retry migration
python3 manage_db.py upgrade
```

### Seeding Fails
- Check database connection
- Ensure migrations are applied
- Check for duplicate keys in seed data

### Can't Access UI
- Ensure you're logged in (`/auth/login`)
- Check server is running
- Verify routes are registered in `app/main.py`

### Auth Not Encrypting
- Verify `CONNECTOR_AUTH_ENCRYPTION_KEY` is set in `.env`
- Key must be 32 url-safe base64-encoded bytes
- Generate new key: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

## Environment Variables

Required:
```env
CONNECTOR_AUTH_ENCRYPTION_KEY=your-32-byte-base64-key
```

Generate a key:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Files to Know

- **Models**: `app/features/connectors/connectors/models.py`
- **Service**: `app/features/connectors/connectors/services/connector_service.py`
- **API Routes**: `app/features/connectors/connectors/routes/api_routes.py`
- **Templates**: `app/features/connectors/connectors/templates/connectors/`
- **Seeding**: `app/seed_connectors.py`

## Support

For issues or questions:
1. Check `README.md` for full API documentation
2. Check `IMPLEMENTATION_SUMMARY.md` for architecture details
3. Review `PROJECT_PLAN_Connectors_Slice.md` for status
4. Check server logs for errors

---

**Ready to go!** 🚀
