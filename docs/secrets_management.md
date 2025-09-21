# 🔐 Secrets Management Guide

This FastAPI template includes a **production-ready secrets management system** that supports multiple backends and provides secure, auditable access to application secrets.

## 🎯 Features

- **Multi-Backend Support**: `.env` files (dev), AWS Secrets Manager, Azure Key Vault
- **Auto-Detection**: Automatically selects appropriate backend based on environment
- **Validation**: Ensures all required secrets are available at startup
- **Caching**: Optional in-memory caching for performance
- **CLI Tools**: Command-line interface for managing secrets
- **Type Safety**: Full type hints and validation
- **Audit Logging**: All secret access is logged

## 🏗️ Architecture

```
SecretsManager (High-level API)
├── EnvFileSecretsProvider (Development)
├── AWSSecretsManagerProvider (Production - AWS)
├── AzureKeyVaultProvider (Production - Azure)
└── HashiCorpVaultProvider (Enterprise)
```

## 🚀 Quick Start

### Development (using .env files)
```bash
# 1. Copy example environment file
cp .env.example .env

# 2. Edit .env with your values
nano .env

# 3. Validate secrets
python3 manage_secrets.py validate

# 4. Start application
python3 -m uvicorn app.main:app --reload
```

### Production (AWS Secrets Manager)
```bash
# 1. Set environment variables
export ENVIRONMENT=production
export SECRETS_BACKEND=AWS_SECRETS_MANAGER
export AWS_REGION=us-east-1

# 2. Store secrets in AWS
aws secretsmanager create-secret --name "DATABASE_URL" --secret-string "postgresql://..."
aws secretsmanager create-secret --name "JWT_SECRET_KEY" --secret-string "your-256-bit-key"

# 3. Validate secrets
python3 manage_secrets.py validate

# 4. Deploy application
```

## 📋 Required Secrets

| Secret Name | Description | Required | Default |
|-------------|-------------|----------|---------|
| `DATABASE_URL` | Database connection string | ✅ | SQLite (dev only) |
| `JWT_SECRET_KEY` | JWT signing key (256+ bits) | ✅ | - |
| `SECRET_KEY` | Application secret key | ✅ | - |

## 🔧 Optional Secrets

| Secret Name | Description | Required | Default |
|-------------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key | ❌ | - |
| `FIRECRAWL_API_KEY` | Firecrawl API key | ❌ | - |
| `HUNTER_API_KEY` | Hunter.io API key | ❌ | - |
| `EMAIL_HOST` | SMTP server hostname | ❌ | smtp.gmail.com |
| `EMAIL_PASSWORD` | SMTP password | ❌ | - |
| `SENTRY_DSN` | Error tracking DSN | ❌ | - |

## 🛠️ CLI Commands

### Validate Secrets
```bash
python3 manage_secrets.py validate
```

### List All Secrets
```bash
python3 manage_secrets.py list
```

### Check Environment
```bash
python3 manage_secrets.py check
```

### Get Secret (masked)
```bash
python3 manage_secrets.py get JWT_SECRET_KEY
```

### Set Secret
```bash
python3 manage_secrets.py set NEW_SECRET_KEY "secret-value"
```

### Generate Template
```bash
python3 manage_secrets.py template
```

## 🌩️ Cloud Provider Setup

### AWS Secrets Manager

1. **Install dependencies**:
```bash
pip install boto3>=1.28.0
```

2. **Configure AWS credentials**:
```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-east-1
```

3. **Create secrets**:
```bash
aws secretsmanager create-secret --name "DATABASE_URL" --secret-string "postgresql://..."
aws secretsmanager create-secret --name "JWT_SECRET_KEY" --secret-string "$(openssl rand -base64 32)"
```

4. **Set backend**:
```bash
export SECRETS_BACKEND=AWS_SECRETS_MANAGER
```

### Azure Key Vault

1. **Install dependencies**:
```bash
pip install azure-keyvault-secrets>=4.7.0 azure-identity>=1.14.0
```

2. **Configure Azure credentials**:
```bash
export AZURE_CLIENT_ID=your-client-id
export AZURE_CLIENT_SECRET=your-client-secret
export AZURE_TENANT_ID=your-tenant-id
export AZURE_KEY_VAULT_URL=https://your-vault.vault.azure.net/
```

3. **Create secrets**:
```bash
az keyvault secret set --vault-name your-vault --name "DATABASE-URL" --value "postgresql://..."
az keyvault secret set --vault-name your-vault --name "JWT-SECRET-KEY" --value "$(openssl rand -base64 32)"
```

4. **Set backend**:
```bash
export SECRETS_BACKEND=AZURE_KEY_VAULT
```

## 💻 Programming Interface

### Basic Usage
```python
from app.core.secrets_manager import get_secrets_manager

# Get secrets manager
manager = get_secrets_manager()

# Get a single secret
secret_value = await manager.get_secret("JWT_SECRET_KEY")

# Get multiple secrets
secrets = await manager.get_secrets(["DATABASE_URL", "JWT_SECRET_KEY"])

# Get configuration objects
jwt_config = await manager.get_jwt_config()
api_keys = await manager.get_api_keys()
```

### Convenience Functions
```python
from app.core.secrets_manager import get_secret, get_database_url

# Get any secret
value = await get_secret("OPENAI_API_KEY", required=False)

# Get database URL with fallback
db_url = await get_database_url()
```

### Custom Secrets
```python
from app.core.secrets import SECRETS_REGISTRY, SecretMetadata

# Register new secret
SECRETS_REGISTRY["MY_SECRET"] = SecretMetadata(
    name="MY_SECRET",
    description="My custom secret",
    required=True
)
```

## 🔒 Security Best Practices

### Development
- ✅ Use `.env` files for local development
- ✅ Add `.env` to `.gitignore`
- ✅ Use example files (`.env.example`) for documentation
- ❌ Never commit actual secret values to git

### Production
- ✅ Use dedicated secrets management service
- ✅ Enable audit logging
- ✅ Use IAM roles, not user credentials
- ✅ Implement secret rotation
- ✅ Monitor secret access patterns
- ❌ Never use `.env` files in production
- ❌ Never log secret values

### Secret Generation
```bash
# Generate strong secrets
openssl rand -base64 32  # 256-bit key
openssl rand -hex 32     # 256-bit hex key
uuidgen                  # UUID
```

## 🔄 Backend Configuration

### Auto-Detection Logic
1. Check `SECRETS_BACKEND` environment variable
2. If `ENVIRONMENT=production`:
   - AWS: Check for `AWS_REGION` or `AWS_DEFAULT_REGION`
   - Azure: Check for `AZURE_SUBSCRIPTION_ID` or `AZURE_CLIENT_ID`
3. Fallback to `ENV_FILE`

### Manual Configuration
```bash
# Force specific backend
export SECRETS_BACKEND=AWS_SECRETS_MANAGER
export SECRETS_BACKEND=AZURE_KEY_VAULT
export SECRETS_BACKEND=ENV_FILE
```

## 🧪 Testing

### Unit Tests
```python
import pytest
from app.core.secrets_manager import SecretsManager, SecretsBackend

@pytest.mark.asyncio
async def test_secrets_manager():
    manager = SecretsManager(backend=SecretsBackend.ENV_FILE)
    value = await manager.get_secret("TEST_SECRET", required=False)
    assert value is None or isinstance(value, str)
```

### Integration Tests
```bash
# Test with different backends
SECRETS_BACKEND=ENV_FILE python3 manage_secrets.py validate
SECRETS_BACKEND=AWS_SECRETS_MANAGER python3 manage_secrets.py validate
```

## 🚨 Troubleshooting

### Common Issues

**Secret not found**:
```bash
# Check if secret exists
python3 manage_secrets.py get SECRET_NAME

# Validate all secrets
python3 manage_secrets.py validate
```

**Provider connection failed**:
```bash
# Check environment configuration
python3 manage_secrets.py check

# Test provider health
python3 -c "from app.core.secrets_manager import get_secrets_manager; print(get_secrets_manager().health_check())"
```

**AWS permissions**:
```bash
# Test AWS access
aws secretsmanager list-secrets

# Check IAM permissions
aws sts get-caller-identity
```

**Azure permissions**:
```bash
# Test Azure access
az keyvault secret list --vault-name your-vault

# Check login status
az account show
```

## 📊 Monitoring

### Application Startup
The application validates all required secrets at startup and logs the results:

```
INFO: All required secrets are available
INFO: Using secrets backend: aws_secrets_manager
```

### Health Checks
```bash
curl http://localhost:8000/health/detailed
```

### Logs
All secret access is logged (without exposing values):
```
INFO: Retrieved secret: JWT_SECRET_KEY
ERROR: Failed to get secret MISSING_SECRET: Secret not found
```

## 🔄 Migration Guide

### From .env to AWS Secrets Manager

1. **Backup current secrets**:
```bash
python3 manage_secrets.py template > backup.env
```

2. **Create secrets in AWS**:
```bash
# Read from .env and create in AWS
source .env
aws secretsmanager create-secret --name "DATABASE_URL" --secret-string "$DATABASE_URL"
aws secretsmanager create-secret --name "JWT_SECRET_KEY" --secret-string "$JWT_SECRET_KEY"
```

3. **Update environment**:
```bash
export SECRETS_BACKEND=AWS_SECRETS_MANAGER
export AWS_REGION=us-east-1
```

4. **Validate migration**:
```bash
python3 manage_secrets.py validate
```

---

## 🎯 Next Steps

1. **Choose your production backend** (AWS/Azure/Vault)
2. **Set up cloud credentials** and permissions
3. **Migrate development secrets** to production backend
4. **Implement secret rotation** procedures
5. **Set up monitoring** and alerting
6. **Train your team** on secrets management practices

Your secrets are now production-ready! 🎉
