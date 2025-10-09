#!/usr/bin/env python3
"""
Automated Slice Generator for Terra Automation Platform

This script generates a complete vertical slice from a template, automatically handling:
- File structure creation
- Template variable replacement
- Static file mounting
- Route registration
- Database model registration

Usage:
    python scripts/create_slice.py <domain> <slice_name> [options]

Examples:
    python scripts/create_slice.py business_automations email_campaigns
    python scripts/create_slice.py administration api_keys
    python scripts/create_slice.py core notifications --no-static
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import re

class SliceGenerator:
    """Generates vertical slices from templates."""

    def __init__(self, workspace_root: str = None):
        self.workspace_root = Path(workspace_root or os.getcwd())
        self.template_slice_path = self.workspace_root / "app/features/administration/smtp"

    def create_slice(self, domain: str, slice_name: str, options: Dict = None):
        """Create a new slice from template."""
        options = options or {}

        print(f"🚀 Creating new slice: {domain}/{slice_name}")

        # Validate inputs
        self._validate_inputs(domain, slice_name)

        # Calculate paths
        target_path = self.workspace_root / f"app/features/{domain}/{slice_name}"

        # Check if slice already exists
        if target_path.exists():
            raise ValueError(f"Slice already exists: {target_path}")

        # Create slice from template
        self._copy_template_structure(target_path, domain, slice_name, options)

        # Generate content with replacements
        self._process_template_files(target_path, domain, slice_name, options)

        # Register in main app
        self._register_slice(domain, slice_name, options)

        # Update database imports
        self._update_database_imports(domain, slice_name)

        print(f"✅ Slice created successfully: {target_path}")
        print(f"📋 Next steps:")
        print(f"   1. Create migration: alembic revision --autogenerate -m 'Add {slice_name} tables'")
        print(f"   2. Run migration: alembic upgrade head")
        print(f"   3. Restart server to load new routes")
        print(f"   4. Access at: http://localhost:8000/features/{slice_name}/")

    def _validate_inputs(self, domain: str, slice_name: str):
        """Validate input parameters."""
        if not re.match(r'^[a-z_]+$', domain):
            raise ValueError("Domain must contain only lowercase letters and underscores")
        if not re.match(r'^[a-z_]+$', slice_name):
            raise ValueError("Slice name must contain only lowercase letters and underscores")
        if not self.template_slice_path.exists():
            raise ValueError(f"Template slice not found: {self.template_slice_path}")

    def _copy_template_structure(self, target_path: Path, domain: str, slice_name: str, options: Dict):
        """Copy the template structure to target location."""
        print(f"📁 Creating directory structure...")

        # Create target directory
        target_path.mkdir(parents=True, exist_ok=True)

        # Copy core files
        core_files = [
            "__init__.py",
            "models.py",
            "routes.py",
            "services.py"
        ]

        for file_name in core_files:
            src_file = self.template_slice_path / file_name
            dst_file = target_path / file_name
            if src_file.exists():
                shutil.copy2(src_file, dst_file)
                print(f"   ✅ {file_name}")

        # Copy templates directory
        src_templates = self.template_slice_path / "templates"
        dst_templates = target_path / "templates"
        if src_templates.exists():
            shutil.copytree(src_templates, dst_templates)
            print(f"   ✅ templates/")

        # Copy static directory if requested
        if not options.get('no_static', False):
            src_static = self.template_slice_path / "static"
            dst_static = target_path / "static"
            if src_static.exists():
                shutil.copytree(src_static, dst_static)
                print(f"   ✅ static/")
            else:
                # Create minimal static structure
                (dst_static / "js").mkdir(parents=True, exist_ok=True)
                (dst_static / "css").mkdir(parents=True, exist_ok=True)
                print(f"   ✅ static/ (minimal structure)")

    def _process_template_files(self, target_path: Path, domain: str, slice_name: str, options: Dict):
        """Process template files and replace placeholders."""
        print(f"🔄 Processing template files...")

        # Calculate replacement values
        replacements = self._calculate_replacements(domain, slice_name)

        # Process Python files
        python_files = list(target_path.glob("*.py"))
        for file_path in python_files:
            self._process_file(file_path, replacements)
            print(f"   ✅ {file_path.name}")

        # Process template files
        template_files = list((target_path / "templates").rglob("*.html"))
        for file_path in template_files:
            self._process_file(file_path, replacements)
            print(f"   ✅ templates/{file_path.relative_to(target_path / 'templates')}")

        # Rename template directories to match slice
        self._rename_template_directories(target_path, domain, slice_name)

        # Process JavaScript files if they exist
        if (target_path / "static" / "js").exists():
            js_files = list((target_path / "static" / "js").glob("*.js"))
            for file_path in js_files:
                self._process_file(file_path, replacements)
                print(f"   ✅ static/js/{file_path.name}")

    def _calculate_replacements(self, domain: str, slice_name: str) -> Dict[str, str]:
        """Calculate all string replacements for template processing."""
        # Convert to different case formats
        slice_title = slice_name.replace('_', ' ').title()
        slice_pascal = ''.join(word.capitalize() for word in slice_name.split('_'))
        slice_camel = slice_name.replace('_', '')

        return {
            # SMTP-specific patterns (source)
            'smtp': slice_name,
            'SMTP': slice_name.upper(),
            'Smtp': slice_pascal,
            'SMTPConfiguration': f'{slice_pascal}',
            'SMTPConfigurationService': f'{slice_pascal}Service',
            'SMTPStatus': f'{slice_pascal}Status',
            'smtp_configurations': f'{slice_name}s',

            # Template patterns
            '[domain]': domain,
            '[slice_name]': slice_name,
            '[slice_title]': slice_title,
            '[slice_pascal]': slice_pascal,
            '[slice_camel]': slice_camel,

            # Path patterns
            '/administration/smtp': f'/{slice_name}',
            'administration/smtp': f'{slice_name}',
            'app.features.administration.smtp': f'app.features.{domain}.{slice_name}',

            # URL patterns
            f'/features/{slice_name}/static': f'/features/{slice_name}/static',

            # Description patterns
            'SMTP configuration': f'{slice_title} management',
            'SMTP Configuration': f'{slice_title}',
            'smtp configuration': f'{slice_name} configuration'
        }

    def _process_file(self, file_path: Path, replacements: Dict[str, str]):
        """Process a single file with string replacements."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Apply replacements
        for old, new in replacements.items():
            content = content.replace(old, new)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _rename_template_directories(self, target_path: Path, domain: str, slice_name: str):
        """Rename template directories to match the new slice."""
        templates_path = target_path / "templates"

        # Find the old structure (administration/smtp)
        old_path = templates_path / "administration" / "smtp"
        if old_path.exists():
            # Create new structure
            new_path = templates_path / slice_name
            new_path.mkdir(parents=True, exist_ok=True)

            # Move files
            for item in old_path.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(old_path)
                    new_file = new_path / rel_path
                    new_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(item), str(new_file))

            # Remove old structure
            shutil.rmtree(templates_path / "administration")
            print(f"   🔄 Renamed templates: administration/smtp → {slice_name}")

    def _register_slice(self, domain: str, slice_name: str, options: Dict):
        """Register the slice in main.py."""
        main_py_path = self.workspace_root / "app/main.py"

        with open(main_py_path, 'r') as f:
            content = f.read()

        # Add import
        import_line = f"from .features.{domain}.{slice_name}.routes import router as {slice_name}_router"

        # Find imports section
        if "content_broadcaster_router" in content:
            # Add after content broadcaster import
            content = content.replace(
                "from .features.business_automations.content_broadcaster.routes import router as content_broadcaster_router",
                f"from .features.business_automations.content_broadcaster.routes import router as content_broadcaster_router\n{import_line}"
            )
        else:
            # Add at end of imports
            last_import = content.rfind("import ")
            if last_import != -1:
                end_of_line = content.find("\n", last_import)
                content = content[:end_of_line] + f"\n{import_line}" + content[end_of_line:]

        # Add router registration
        router_line = f'app.include_router({slice_name}_router, prefix="/features/{domain}/{slice_name}", tags=["{domain}"])'

        # Find router registrations section
        if "content_broadcaster_router" in content:
            content = content.replace(
                'app.include_router(content_broadcaster_router, prefix="/features", tags=["business-automations"])',
                f'app.include_router(content_broadcaster_router, prefix="/features", tags=["business-automations"])\n{router_line}'
            )
        else:
            # Add before final app setup
            content = content.replace(
                "# Setup versioned API documentation",
                f"{router_line}\n\n# Setup versioned API documentation"
            )

        # Add static file mounting if needed
        if not options.get('no_static', False):
            static_line = f'app.mount("/features/{slice_name}/static", StaticFiles(directory="app/features/{domain}/{slice_name}/static"), name="{slice_name}_static")'

            # Add after existing static mounts
            if "content_broadcaster_static" in content:
                content = content.replace(
                    'app.mount("/features/content-broadcaster/static", StaticFiles(directory="app/features/business_automations/content_broadcaster/static"), name="content_broadcaster_static")',
                    f'app.mount("/features/content-broadcaster/static", StaticFiles(directory="app/features/business_automations/content_broadcaster/static"), name="content_broadcaster_static")\n{static_line}'
                )
            else:
                # Add after SMTP static mount
                content = content.replace(
                    'app.mount("/features/administration/smtp/static", StaticFiles(directory="app/features/administration/smtp/static"), name="smtp_static")',
                    f'app.mount("/features/administration/smtp/static", StaticFiles(directory="app/features/administration/smtp/static"), name="smtp_static")\n{static_line}'
                )

        with open(main_py_path, 'w') as f:
            f.write(content)

        print(f"   ✅ Registered routes in main.py")
        if not options.get('no_static', False):
            print(f"   ✅ Registered static files in main.py")

    def _update_database_imports(self, domain: str, slice_name: str):
        """Add model import to database.py for table creation."""
        db_py_path = self.workspace_root / "app/features/core/database.py"

        with open(db_py_path, 'r') as f:
            content = f.read()

        # Add import
        import_line = f"import app.features.{domain}.{slice_name}.models"

        # Find model imports section
        if "# Model imports for table creation" in content:
            content = content.replace(
                "# Model imports for table creation",
                f"# Model imports for table creation\n{import_line}"
            )
        else:
            # Add at end of file
            content += f"\n{import_line}\n"

        with open(db_py_path, 'w') as f:
            f.write(content)

        print(f"   ✅ Added model import to database.py")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate a new vertical slice")
    parser.add_argument("domain", help="Domain name (e.g., business_automations, administration)")
    parser.add_argument("slice_name", help="Slice name (e.g., email_campaigns, api_keys)")
    parser.add_argument("--no-static", action="store_true", help="Skip static files creation")
    parser.add_argument("--workspace", help="Workspace root directory (default: current directory)")

    args = parser.parse_args()

    try:
        generator = SliceGenerator(args.workspace)
        options = {
            'no_static': args.no_static
        }
        generator.create_slice(args.domain, args.slice_name, options)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
