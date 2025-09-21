# API Key Management System

The API Key Management system provides secure, scoped access for external systems to integrate with your SaaS platform APIs.

## Overview

### Purpose
- **Inbound API Authentication**: Secure access for customers/partners to your APIs
- **Scoped Permissions**: Granular control over what each API key can access
- **Usage Tracking**: Monitor and rate limit API usage per key
- **Enterprise Security**: HMAC signature verification, automatic expiration

### Distinction from Secrets Management
| Feature | Secrets Management | API Key Management |
|---------|-------------------|-------------------|
| **Direction** | Outbound (you → external) | Inbound (external → you) |
| **Purpose** | Store your credentials | Issue credentials to others |
| **Examples** | Stripe API key, SendGrid token | Customer integration keys |

## Core Features

### 1. **API Key Scopes**
```python
READ        # Read-only access to resources
WRITE       # Create and update resources
ADMIN       # Full administrative access
WEBHOOK     # Webhook and event access
MONITORING  # System monitoring and metrics
```

### 2. **Security Features**
- **Secure Generation**: Cryptographically secure key generation
- **HMAC Signatures**: Request signature verification (optional)
- **Rate Limiting**: Per-hour and per-day limits
- **Automatic Expiration**: Time-based key expiration
- **Usage Tracking**: Monitor key usage and detect abuse

### 3. **Management Features**
- **Tenant Isolation**: Keys are scoped to specific tenants
- **Admin Interface**: Full CRUD operations for administrators
- **Statistics**: Usage analytics and monitoring
- **Revocation**: Instant key deactivation

## Admin API Endpoints

### Authentication
All admin endpoints require admin role authentication:
```http
Authorization: Bearer <admin_jwt_token>
```

### Key Management

#### Create API Key
```http
POST /administration/api-keys/create
Content-Type: application/json

{
  "name": "Customer Integration Key",
  "description": "API key for Acme Corp integration",
  "tenant_id": "acme-corp",
  "scopes": ["read", "write"],
  "expires_in_days": 365,
  "rate_limit_per_hour": 1000,
  "rate_limit_per_day": 10000
}
```

**Response:**
```json
{
  "id": 123,
  "key_id": "ak_abc123def456",
  "name": "Customer Integration Key",
  "tenant_id": "acme-corp",
  "scopes": ["read", "write"],
  "secret": "sk_xyz789uvw012",
  "status": "active",
  "created_at": "2025-01-18T10:00:00Z",
  "expires_at": "2026-01-18T10:00:00Z"
}
```

#### List API Keys
```http
GET /administration/api-keys/list?tenant_id=acme-corp&limit=50
```

#### Get API Key Details
```http
GET /administration/api-keys/ak_abc123def456
```

#### Revoke API Key
```http
POST /administration/api-keys/ak_abc123def456/revoke
```

#### Get Statistics
```http
GET /administration/api-keys/stats
```

**Response:**
```json
{
  "total_keys": 150,
  "active_keys": 142,
  "revoked_keys": 8,
  "expired_keys": 0,
  "total_requests_today": 45230,
  "top_tenants": [
    {"tenant_id": "acme-corp", "usage_count": 15000},
    {"tenant_id": "beta-llc", "usage_count": 12000}
  ]
}
```

## Customer Usage

### 1. **Basic API Authentication**
```bash
# Using API key in Authorization header
curl -X GET "https://api.yourplatform.com/api/v1/users" \
  -H "Authorization: Bearer ak_abc123def456:sk_xyz789uvw012"
```

### 2. **With HMAC Signature (Enhanced Security)**
```python
import hmac
import hashlib
import base64
from datetime import datetime

def generate_signature(method, path, body, timestamp, secret):
    """Generate HMAC signature for request."""
    canonical_string = f"{method}\n{path}\n{body}\n{timestamp}"
    signature = hmac.new(
        secret.encode(),
        canonical_string.encode(),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode()

# Make authenticated request with signature
method = "POST"
path = "/api/v1/users"
body = '{"email": "john@example.com", "role": "user"}'
timestamp = datetime.utcnow().isoformat()
secret = "sk_xyz789uvw012"

signature = generate_signature(method, path, body, timestamp, secret)

headers = {
    "Authorization": "Bearer ak_abc123def456:sk_xyz789uvw012",
    "X-Signature": f"sha256={signature}",
    "X-Timestamp": timestamp,
    "Content-Type": "application/json"
}

response = requests.post(
    "https://api.yourplatform.com/api/v1/users",
    data=body,
    headers=headers
)
```

### 3. **JavaScript/Node.js Example**
```javascript
const crypto = require('crypto');
const axios = require('axios');

class APIClient {
  constructor(keyId, secret, baseURL) {
    this.keyId = keyId;
    this.secret = secret;
    this.baseURL = baseURL;
  }

  generateSignature(method, path, body, timestamp) {
    const canonicalString = `${method}\n${path}\n${body}\n${timestamp}`;
    const signature = crypto
      .createHmac('sha256', this.secret)
      .update(canonicalString)
      .digest('base64');
    return signature;
  }

  async request(method, path, data = null) {
    const timestamp = new Date().toISOString();
    const body = data ? JSON.stringify(data) : '';
    const signature = this.generateSignature(method, path, body, timestamp);

    const headers = {
      'Authorization': `Bearer ${this.keyId}:${this.secret}`,
      'X-Signature': `sha256=${signature}`,
      'X-Timestamp': timestamp,
      'Content-Type': 'application/json'
    };

    return axios({
      method,
      url: `${this.baseURL}${path}`,
      data,
      headers
    });
  }
}

// Usage
const client = new APIClient(
  'ak_abc123def456',
  'sk_xyz789uvw012',
  'https://api.yourplatform.com'
);

// Create user
const response = await client.request('POST', '/api/v1/users', {
  email: 'john@example.com',
  role: 'user'
});
```

## Error Handling

### Common Error Responses

#### Invalid API Key Format
```json
{
  "detail": "Invalid API key format. Expected 'keyid:secret'"
}
```

#### Invalid or Expired Key
```json
{
  "detail": "Invalid or expired API key"
}
```

#### Insufficient Scope
```json
{
  "detail": "API key does not have required scope: write"
}
```

#### Rate Limit Exceeded
```json
{
  "detail": "Rate limit exceeded. Try again later."
}
```

## Security Best Practices

### For Platform Administrators

1. **Principle of Least Privilege**: Only grant necessary scopes
2. **Regular Rotation**: Set appropriate expiration dates
3. **Monitor Usage**: Watch for unusual activity patterns
4. **Audit Access**: Track key creation and usage

### For API Key Users

1. **Secure Storage**: Never commit keys to version control
2. **Environment Variables**: Store keys as environment variables
3. **HTTPS Only**: Always use HTTPS for API requests
4. **Signature Verification**: Use HMAC signatures for sensitive operations
5. **Error Handling**: Implement proper retry logic for rate limits

## Integration with Existing Systems

### Webhook Authentication
API keys can be used to authenticate webhook deliveries:

```python
# In webhook endpoint
@router.post("/webhook")
async def webhook_handler(
    request: Request,
    api_key: APIKeyInfo = Depends(require_webhook_scope)
):
    # Webhook is authenticated and authorized
    tenant_id = api_key.tenant_id
    # Process webhook for specific tenant
```

### Service-to-Service Communication
Use API keys for backend service communication:

```python
# Service A calling Service B
headers = {
    "Authorization": f"Bearer {service_api_key}",
    "X-Service": "user-service"
}
response = await http_client.post("/api/v1/internal/sync", headers=headers)
```

## Monitoring and Analytics

### Usage Metrics
- Total requests per key
- Success/failure rates
- Rate limit violations
- Geographic distribution (if implemented)

### Security Monitoring
- Failed authentication attempts
- Signature verification failures
- Unusual usage patterns
- Potential abuse detection

## Migration and Deployment

### Database Migrations
API keys are stored in the `api_keys` table. Run migrations:

```bash
alembic upgrade head
```

### Configuration
Set rate limiting defaults in environment:

```env
DEFAULT_RATE_LIMIT_PER_HOUR=1000
DEFAULT_RATE_LIMIT_PER_DAY=10000
MAX_API_KEY_EXPIRATION_DAYS=365
```

## Troubleshooting

### Common Issues

1. **404 on API Key Endpoints**: Ensure routes are properly mounted
2. **Signature Mismatches**: Check timestamp format and canonical string construction
3. **Rate Limiting**: Implement exponential backoff in client code
4. **Scope Errors**: Verify key has required permissions for endpoint

### Debug Mode
Enable detailed logging for debugging:

```python
import logging
logging.getLogger("app.core.api_security").setLevel(logging.DEBUG)
```

This provides comprehensive API key management for enterprise SaaS platforms with security, monitoring, and ease of use.