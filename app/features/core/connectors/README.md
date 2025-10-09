# Connector + Secrets Integration

## 🔐 How It Works

The connector system now seamlessly integrates with the secrets manager to provide secure credential storage and resolution. Here's how it works:

### 1. **Simple Credential Resolution**
Instead of a separate service, we added credential resolution directly to the existing `ConnectorService`:

```python
# In app/features/connectors/connectors/services.py
async def get_connector_credentials(self, connector_id: int) -> Dict[str, Any]:
    """Resolves credentials from configuration + secrets manager"""

async def create_sdk_connector_instance(self, connector_id: int):
    """Creates SDK connector with resolved credentials"""

async def test_connector_connection(self, connector_id: int):
    """Tests connection using SDK with resolved credentials"""
```

### 2. **Tenant-Aware by Design**
All credential resolution is automatically tenant-scoped since the `ConnectorService` requires a `tenant_id`.

### 3. **Two Ways to Store Credentials**

#### Option A: Direct Configuration (Simple API Keys)
```json
{
  "configuration": {
    "api_key": "sk-your-api-key-here",
    "model": "gpt-3.5-turbo"
  }
}
```

#### Option B: Secrets Manager References (Secure)
```json
{
  "configuration": {
    "model": "gpt-3.5-turbo"
  },
  "secrets_references": {
    "api_key": {
      "secret_name": "openai_api_key"
    }
  }
}
```

## 🎯 Usage Examples

### Creating a Connector with Secrets

```python
# 1. Create secret in secrets manager
secret = await secrets_service.create_secret(
    tenant_id=tenant_id,
    secret_data=SecretCreate(
        name="openai_api_key",
        secret_type=SecretType.API_KEY,
        value="sk-your-actual-key"
    )
)

# 2. Create connector that references the secret
connector = await connector_service.create_tenant_connector(
    TenantConnectorCreate(
        available_connector_id=1,  # OpenAI
        instance_name="My AI Assistant",
        configuration={
            "default_model": "gpt-3.5-turbo"
        },
        secrets_references={
            "api_key": {"secret_name": "openai_api_key"}
        }
    )
)

# 3. Use the connector - credentials are resolved automatically
sdk_connector = await connector_service.create_sdk_connector_instance(connector.id)
result = await sdk_connector.generate_text("Hello world!")
```

### Testing Connections

```python
# Test connection using resolved credentials
test_result = await connector_service.test_connector_connection(connector_id)

if test_result["success"]:
    print("✓ Connection successful!")
else:
    print(f"✗ Failed: {test_result['error']}")
```

## 🎛️ UI Integration

### 1. **Test Connection Button**
- Added to connector edit forms
- Added to table actions in connector list
- Shows real-time connection status

### 2. **New API Endpoints**
```
POST /features/connectors/{id}/test-connection
GET  /features/connectors/{id}/credentials
POST /features/connectors/{id}/create-sdk-instance
```

### 3. **Enhanced Categories**
Added support for new connector types:
- AI/ML (ai_ml)
- Data Extraction (data_extraction)

## 🚀 Available SDK Connectors

### OpenAI
```python
credentials = {"api_key": "sk-..."}
connector = get_connector("openai", credentials)
await connector.generate_text("Hello!")
await connector.create_embeddings(["text1", "text2"])
```

### Anthropic Claude
```python
credentials = {"api_key": "sk-ant-..."}
connector = get_connector("anthropic", credentials)
await connector.generate_text("Hello!", model="claude-3-haiku-20240307")
```

### Firecrawl
```python
credentials = {"api_key": "fc-..."}
connector = get_connector("firecrawl", credentials)
await connector.scrape_url("https://example.com")
```

## 🔒 Security Features

### Credential Masking
When viewing credentials through the API, sensitive values are automatically masked:
```json
{
  "api_key": "***key123",
  "model": "gpt-3.5-turbo"
}
```

### Access Tracking
Every time credentials are accessed, it's logged in the secrets manager:
- Who accessed it (`connector_{id}`)
- When it was accessed
- Access count tracking

### Automatic Cleanup
SDK connectors automatically clean up resources:
```python
try:
    result = await sdk_connector.generate_text("...")
finally:
    await sdk_connector.cleanup()  # Always called
```

## 📝 Next Steps

1. **Add more SDK connectors** (Google, Azure, etc.)
2. **Implement credential rotation** for expired API keys
3. **Add connector health monitoring** with periodic connection tests
4. **Create connector templates** for common configurations

The system is now ready for production use with secure, tenant-aware credential management! 🎉
