#!/usr/bin/env python3
"""
Secrets management CLI tool for the FastAPI template.
Helps with setting up, validating, and managing secrets across environments.
"""
import asyncio
import argparse
import sys
import json
from typing import Dict, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

try:
    from app.features.core.secrets_manager import get_secrets_manager, SECRETS_REGISTRY
    from app.features.core.secrets import SecretsBackend
except ImportError as e:
    logger.error(f"Failed to import secrets modules: {e}")
    logger.error("Make sure you're running this from the project root directory")
    sys.exit(1)


async def validate_secrets():
    """Validate all required secrets are available."""
    logger.info("Validating secrets...")

    try:
        manager = get_secrets_manager()

        # Health check
        if not manager.health_check():
            logger.error("❌ Secrets provider health check failed")
            return False

        logger.info(f"✅ Secrets provider ({manager.backend.value}) is healthy")

        # Validate required secrets
        validation_results = await manager.validate_all_required_secrets()

        all_valid = True
        for secret_name, is_available in validation_results.items():
            status = "✅" if is_available else "❌"
            logger.info(f"{status} {secret_name}: {'Available' if is_available else 'Missing'}")
            if not is_available:
                all_valid = False

        if all_valid:
            logger.info("🎉 All required secrets are available!")
        else:
            logger.error("💥 Some required secrets are missing")

        return all_valid

    except Exception as e:
        logger.error(f"❌ Secrets validation failed: {e}")
        return False


async def list_secrets():
    """List all registered secrets with their metadata."""
    logger.info("Registered secrets:")

    for name, metadata in SECRETS_REGISTRY.items():
        required_text = "Required" if metadata.required else "Optional"
        default_text = f" (default: {metadata.default})" if metadata.default else ""
        logger.info(f"  {name}: {metadata.description} [{required_text}]{default_text}")


async def get_secret_value(secret_name: str):
    """Get and display a secret value (masked)."""
    try:
        manager = get_secrets_manager()
        value = await manager.get_secret(secret_name, required=False)

        if value is None:
            logger.info(f"❌ Secret '{secret_name}' not found")
        else:
            # Mask the value for security
            if len(value) > 8:
                masked_value = value[:4] + "..." + value[-4:]
            else:
                masked_value = "***"
            logger.info(f"✅ {secret_name}: {masked_value}")

    except Exception as e:
        logger.error(f"❌ Failed to get secret '{secret_name}': {e}")


async def set_secret_value(secret_name: str, secret_value: str):
    """Set a secret value."""
    try:
        manager = get_secrets_manager()
        success = await manager.set_secret(secret_name, secret_value)

        if success:
            logger.info(f"✅ Successfully set secret '{secret_name}'")
        else:
            logger.error(f"❌ Failed to set secret '{secret_name}'")

    except Exception as e:
        logger.error(f"❌ Failed to set secret '{secret_name}': {e}")


async def check_environment():
    """Check the current environment configuration."""
    import os

    logger.info("Environment Configuration:")
    logger.info(f"  ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set')}")
    logger.info(f"  SECRETS_BACKEND: {os.getenv('SECRETS_BACKEND', 'auto-detected')}")

    # Cloud provider detection
    if os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION'):
        logger.info(f"  AWS Region: {os.getenv('AWS_REGION', os.getenv('AWS_DEFAULT_REGION'))}")

    if os.getenv('AZURE_SUBSCRIPTION_ID'):
        logger.info(f"  Azure Subscription: {os.getenv('AZURE_SUBSCRIPTION_ID')}")

    if os.getenv('AZURE_KEY_VAULT_URL'):
        logger.info(f"  Azure Key Vault: {os.getenv('AZURE_KEY_VAULT_URL')}")

    # Test manager initialization
    try:
        manager = get_secrets_manager()
        logger.info(f"  Detected Backend: {manager.backend.value}")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize secrets manager: {e}")


async def generate_template():
    """Generate a secrets template for the current environment."""
    logger.info("Generating secrets template...")

    template_lines = [
        "# Secrets Template",
        "# Fill in actual values and load into your secrets manager",
        "",
    ]

    for name, metadata in SECRETS_REGISTRY.items():
        template_lines.append(f"# {metadata.description}")
        required_text = " (REQUIRED)" if metadata.required else " (optional)"
        template_lines.append(f"# {required_text}")

        if metadata.default:
            template_lines.append(f"{name}={metadata.default}")
        else:
            template_lines.append(f"{name}=your-{name.lower().replace('_', '-')}-here")
        template_lines.append("")

    template_content = "\n".join(template_lines)

    with open("secrets.template", "w") as f:
        f.write(template_content)

    logger.info("✅ Template generated: secrets.template")


def main():
    parser = argparse.ArgumentParser(description="Secrets management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate all required secrets")

    # List command
    list_parser = subparsers.add_parser("list", help="List all registered secrets")

    # Get command
    get_parser = subparsers.add_parser("get", help="Get a secret value (masked)")
    get_parser.add_argument("secret_name", help="Name of the secret to retrieve")

    # Set command
    set_parser = subparsers.add_parser("set", help="Set a secret value")
    set_parser.add_argument("secret_name", help="Name of the secret to set")
    set_parser.add_argument("secret_value", help="Value of the secret")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check environment configuration")

    # Template command
    template_parser = subparsers.add_parser("template", help="Generate secrets template")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "validate":
            result = asyncio.run(validate_secrets())
            sys.exit(0 if result else 1)
        elif args.command == "list":
            asyncio.run(list_secrets())
        elif args.command == "get":
            asyncio.run(get_secret_value(args.secret_name))
        elif args.command == "set":
            asyncio.run(set_secret_value(args.secret_name, args.secret_value))
        elif args.command == "check":
            asyncio.run(check_environment())
        elif args.command == "template":
            asyncio.run(generate_template())
    except KeyboardInterrupt:
        logger.info("Operation cancelled")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
