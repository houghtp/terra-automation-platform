FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including PowerShell Core
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    wget \
    apt-transport-https \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Install PowerShell Core
# Download the Microsoft repository GPG keys
RUN wget -q https://packages.microsoft.com/config/debian/11/packages-microsoft-prod.deb && \
    dpkg -i packages-microsoft-prod.deb && \
    rm packages-microsoft-prod.deb

# Update the list of packages and install PowerShell
RUN apt-get update && apt-get install -y --no-install-recommends \
    powershell \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install PowerShell modules for M365 CIS compliance checks
RUN chmod +x /app/scripts/install_powershell_modules.sh && \
    /app/scripts/install_powershell_modules.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/fastapi_template
ENV PSModulePath=/usr/local/share/powershell/Modules:/usr/share/powershell/Modules

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
