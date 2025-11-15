"""Auth services module."""

# Import AuthService from sibling services.py file to maintain backward compatibility
import sys
from pathlib import Path

# Get the parent directory (auth/) to import from services.py
auth_dir = Path(__file__).parent.parent

# Import from services.py (not services/ directory)
import importlib.util
spec = importlib.util.spec_from_file_location("auth_services", auth_dir / "services.py")
auth_services_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth_services_module)

AuthService = auth_services_module.AuthService

__all__ = ['AuthService']
