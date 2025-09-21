"""
API Key utility for checking API key status
"""

import os
import logging
from typing import Dict
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

# Try to import admin_required, fall back to a passthrough dependency if not available
try:
    from app.features.core.auth import admin_required
except ImportError:
    # Create a passthrough dependency if admin auth not implemented
    def admin_required():
        pass

# Set up logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api-keys", tags=["utils"])

# Initialize templates
templates = Jinja2Templates(directory="app/core/templates")

def load_and_validate_api_keys():
    """
    Load and validate API keys from environment variables
    
    Returns:
        Dict with API key status and validation details
    """
    # Try to use the centralized API key loading function if available
    try:
        from app.candidates.utils.TerraITAgent.utils.api_clients import load_api_keys
        raw_keys = load_api_keys()
        logger.info("API keys loaded from TerraITAgent centralized utility")
    except ImportError:
        # Fall back to direct environment access
        raw_keys = {
            "openai": os.environ.get("OPENAI_API_KEY", ""),
            "firecrawl": os.environ.get("FIRECRAWL_API_KEY", ""),
            "hunter": os.environ.get("HUNTER_API_KEY", ""),
        }
        logger.info("API keys loaded directly from environment")
    
    # Convert to boolean presence indicators
    api_keys = {k: bool(v) for k, v in raw_keys.items()}
    
    # Check for missing keys
    missing_keys = [key for key, value in api_keys.items() if not value]
    
    # Check for placeholder keys
    placeholder_patterns = ["your_", "placeholder", "add_your", "your-key", "test_key", "sk-placeholder"]
    placeholder_keys = []
    
    for key_name, key_value in raw_keys.items():
        if key_value and any(pattern in key_value.lower() for pattern in placeholder_patterns):
            placeholder_keys.append(key_name)
    
    # Log warnings if needed
    if missing_keys:
        logger.warning(f"Missing API keys: {', '.join(missing_keys)}")
    
    if placeholder_keys:
        logger.warning(f"Found placeholder API keys: {', '.join(placeholder_keys)}")
    
    return {
        "api_key_status": api_keys,
        "missing_keys": missing_keys,
        "placeholder_keys": placeholder_keys,
        "message": _generate_status_message(missing_keys, placeholder_keys)
    }

def _generate_status_message(missing_keys, placeholder_keys):
    """Generate a user-friendly status message"""
    if missing_keys and placeholder_keys:
        return f"Missing API keys: {', '.join(missing_keys)}. Placeholder API keys: {', '.join(placeholder_keys)}. Update your .env file."
    elif missing_keys:
        return f"Missing API keys: {', '.join(missing_keys)}. Add them to your .env file."
    elif placeholder_keys:
        return f"Found placeholder API keys: {', '.join(placeholder_keys)}. Replace with valid API keys in your .env file."
    else:
        return "All required API keys are configured"

@router.get("/status", dependencies=[Depends(admin_required)])
async def check_api_key_status():
    """Check status of API keys for debugging purposes"""
    validation_result = load_and_validate_api_keys()
    
    return validation_result
