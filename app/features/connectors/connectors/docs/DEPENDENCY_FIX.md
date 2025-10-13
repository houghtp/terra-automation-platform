# Dependency Fix: jsonschema

## Issue
Server failed to start with error:
```
ModuleNotFoundError: No module named 'jsonschema'
```

## Root Cause
The `jsonschema` library is required by `ConnectorService` for validating connector configurations against JSON Schema definitions, but was not listed in `requirements.txt`.

## Solution
Added `jsonschema>=4.17.0` to `requirements.txt`:

```diff
cryptography>=41.0.0              # Encryption for sensitive data (SMTP passwords, connector auth)
qrcode>=7.4.2                     # QR code generation for MFA
pyotp>=2.9.0                      # TOTP/HOTP generation for MFA
+jsonschema>=4.17.0                # JSON Schema validation for connector configs
```

## Verification
```bash
# Install the dependency
pip install -r requirements.txt

# Or just install jsonschema
pip install jsonschema>=4.17.0

# Verify installation
python3 -c "import jsonschema; print(jsonschema.__version__)"
```

## Why jsonschema is Needed

The `jsonschema` library is used in `ConnectorService.validate_config()` to validate user-provided connector configurations against the schema stored in the catalog:

```python
async def validate_config(
    self, catalog_key: str, config: Dict[str, Any]
) -> ConfigValidationResponse:
    """Validate config against catalog schema"""
    catalog = await self._get_catalog_by_key(catalog_key)

    try:
        jsonschema.validate(config, catalog.default_config_schema)
        return ConfigValidationResponse(valid=True, errors=[], warnings=[])
    except ValidationError as e:
        return ConfigValidationResponse(valid=False, errors=[str(e)], warnings=[])
```

**Example Use Case:**
- Twitter connector requires `account_label` field
- WordPress connector requires `site_url` and `username` fields
- JSON Schema validation ensures users provide all required fields with correct types before creating/updating connectors

## Status
✅ Fixed - Server now starts successfully with all connectors functionality working.

## Deployment Notes
When deploying to production:
1. Run `pip install -r requirements.txt` to ensure jsonschema is installed
2. Or use Docker and rebuild the image to include the new dependency
3. Verify with health check: `curl http://your-server/health`
