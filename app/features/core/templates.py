import os
import glob
from pathlib import Path
from fastapi.templating import Jinja2Templates
from typing import List

def discover_template_directories() -> List[str]:
    """
    Automatically discover all template directories in the features structure.

    This function scans the app/features directory structure and finds all
    'templates' directories, automatically including them in the Jinja2Templates
    configuration. This eliminates the need to manually add each new slice.

    Returns:
        List[str]: List of template directory paths
    """
    template_dirs = []

    # Always include the main app templates directory
    if os.path.exists("app/templates"):
        template_dirs.append("app/templates")

    # Discover all template directories in the features structure
    features_base = Path("app/features")
    if features_base.exists():
        # Find all 'templates' directories recursively
        template_patterns = [
            "app/features/*/templates",           # Direct feature templates
            "app/features/*/*/templates",         # Nested feature templates
            "app/features/*/*/*/templates",       # Deeply nested templates
        ]

        for pattern in template_patterns:
            template_paths = glob.glob(pattern)
            for path in template_paths:
                if os.path.isdir(path):
                    template_dirs.append(path)

    # Sort for consistent ordering
    template_dirs.sort()

    return template_dirs

# Automatically discover and configure all template directories
TEMPLATE_DIRS = discover_template_directories()

# Create the global Jinja2Templates instance
templates = Jinja2Templates(directory=TEMPLATE_DIRS)
