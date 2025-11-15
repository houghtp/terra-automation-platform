import os
import glob
import re
from pathlib import Path
from fastapi.templating import Jinja2Templates
from typing import List
from markupsafe import Markup

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


def format_procedure(text: str) -> str:
    """
    Format audit procedures and remediation text with natural breakpoints.

    Detects patterns like:
    - "To remediate using the UI:" followed by numbered lists
    - "UI:" followed by numbered lists
    - "PowerShell:" followed by numbered lists
    - Numbered lists (1. 2. 3. etc.)

    Args:
        text: Raw text to format

    Returns:
        Formatted HTML with proper line breaks and indentation
    """
    if not text:
        return ""

    # Escape HTML to prevent XSS
    text = str(text)

    # Detect breakpoint patterns (UI:, PowerShell:, etc.) followed by content
    # Pattern: "To remediate using the UI:" or just "UI:" followed by numbered list
    patterns = [
        (r'(To remediate using the UI:)', r'<strong>\1</strong><br>'),
        (r'(To remediate using PowerShell:)', r'<strong>\1</strong><br>'),
        (r'(To audit using the UI:)', r'<strong>\1</strong><br>'),
        (r'(To audit using PowerShell:)', r'<strong>\1</strong><br>'),
        (r'\b(UI:)(?=\s)', r'<strong>\1</strong><br>'),
        (r'\b(PowerShell:)(?=\s)', r'<strong>\1</strong><br>'),
        (r'\b(CLI:)(?=\s)', r'<strong>\1</strong><br>'),
        (r'\b(Azure Portal:)(?=\s)', r'<strong>\1</strong><br>'),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)

    # Format numbered lists: "1. Item" -> add line break before
    # But not if it's at the start of text or already has a <br> before it
    text = re.sub(r'(?<!^)(?<!<br>)(\d+\.)\s', r'<br>\1 ', text)

    # Format nested numbered lists with indentation
    # Pattern: "4. To create... 1. Select..." -> indent the nested "1."
    lines = text.split('<br>')
    formatted_lines = []
    in_nested_list = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if this is a top-level numbered item (starts with number + period)
        if re.match(r'^\d+\.', line):
            # If we were in a nested list, we're now out
            in_nested_list = False
            # Check if the line contains text that suggests nested items follow
            if 'To create' in line or 'To add' in line or 'To configure' in line:
                in_nested_list = True
            formatted_lines.append(line)
        # Check if this is a nested numbered item (should be indented)
        elif in_nested_list and re.match(r'^\d+\.', line.lstrip()):
            formatted_lines.append(f'&nbsp;&nbsp;&nbsp;&nbsp;{line}')
        else:
            formatted_lines.append(line)

    result = '<br>'.join(formatted_lines)

    return Markup(result)


# Automatically discover and configure all template directories
TEMPLATE_DIRS = discover_template_directories()

# Create the global Jinja2Templates instance
templates = Jinja2Templates(directory=TEMPLATE_DIRS)

# Register custom filters
templates.env.filters['format_procedure'] = format_procedure
