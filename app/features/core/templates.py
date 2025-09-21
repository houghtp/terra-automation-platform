from fastapi.templating import Jinja2Templates

# Jinja2Templates with vertical slice directories
TEMPLATE_DIRS = [
    "app/templates",
    "app/features/core/templates",  # Core shared templates and components
    "app/features/auth/templates",  # Auth templates
    "app/features/dashboard/templates",  # Dashboard templates
    "app/features/administration/audit/templates",  # Audit management templates
    "app/features/administration/users/templates",  # Users management templates
    "app/features/administration/tenants/templates",  # Tenant management templates
    "app/features/administration/secrets/templates",  # Secrets management templates
    "app/features/administration/smtp/templates",  # SMTP management templates
    "app/features/administration/api_keys/templates",  # API Keys management templates
    "app/features/administration/logs/templates",  # Logs management templates
    "app/features/administration/tasks/templates",  # Tasks management templates
    # Add more slices as needed
]
templates = Jinja2Templates(directory=TEMPLATE_DIRS)
