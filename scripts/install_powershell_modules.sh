#!/bin/bash
#
# Install PowerShell modules required for M365 CIS compliance scanning
#
# This script installs all necessary PowerShell modules for executing
# M365 CIS Benchmark checks within the Docker container.
#

set -e  # Exit on error

echo "======================================================================"
echo "Installing PowerShell modules for M365 CIS compliance scanning..."
echo "======================================================================"

# Note: Set-ExecutionPolicy is not needed on Linux - it's Windows-only

# Microsoft Graph SDK - Core authentication and API access for Entra ID, Users, Groups, Security
echo ""
echo "[1/6] Installing Microsoft.Graph..."
pwsh -NoLogo -NoProfile -Command "Install-Module Microsoft.Graph -Scope AllUsers -Force -AllowClobber -SkipPublisherCheck -ErrorAction Stop"

# Microsoft Graph Beta SDK - Beta/preview APIs for advanced features and upcoming functionality
echo ""
echo "[2/6] Installing Microsoft.Graph.Beta..."
pwsh -NoLogo -NoProfile -Command "Install-Module Microsoft.Graph.Beta -Scope AllUsers -Force -AllowClobber -SkipPublisherCheck -ErrorAction Stop"

# Exchange Online Management - Exchange mailbox, security, and compliance settings
echo ""
echo "[3/6] Installing ExchangeOnlineManagement..."
pwsh -NoLogo -NoProfile -Command "Install-Module ExchangeOnlineManagement -Scope AllUsers -Force -AllowClobber -SkipPublisherCheck -ErrorAction Stop"

# Microsoft Teams - Teams policies, settings, and configurations
echo ""
echo "[4/6] Installing MicrosoftTeams..."
pwsh -NoLogo -NoProfile -Command "Install-Module MicrosoftTeams -Scope AllUsers -Force -AllowClobber -SkipPublisherCheck -ErrorAction Stop"

# PnP PowerShell - SharePoint Online sites, libraries, and configurations
echo ""
echo "[5/6] Installing PnP.PowerShell..."
pwsh -NoLogo -NoProfile -Command "Install-Module PnP.PowerShell -Scope AllUsers -Force -AllowClobber -SkipPublisherCheck -ErrorAction Stop"

# Power BI Management - Power BI tenant settings and admin APIs (includes Fabric)
echo ""
echo "[6/6] Installing MicrosoftPowerBIMgmt..."
pwsh -NoLogo -NoProfile -Command "Install-Module MicrosoftPowerBIMgmt -Scope AllUsers -Force -AllowClobber -SkipPublisherCheck -ErrorAction Stop"

echo ""
echo "======================================================================"
echo "PowerShell modules installation completed successfully!"
echo "======================================================================"

# Verify installations
echo ""
echo "Verifying installed modules..."
pwsh -NoLogo -NoProfile -Command "
    \$modules = @('Microsoft.Graph', 'Microsoft.Graph.Beta', 'ExchangeOnlineManagement', 'MicrosoftTeams', 'PnP.PowerShell', 'MicrosoftPowerBIMgmt')
    foreach (\$module in \$modules) {
        \$installed = Get-Module -ListAvailable -Name \$module | Select-Object -First 1
        if (\$installed) {
            Write-Host \"✓ \$module - Version: \$(\$installed.Version)\" -ForegroundColor Green
        } else {
            Write-Host \"✗ \$module - NOT INSTALLED\" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host \"\"
    Write-Host \"All modules verified successfully!\" -ForegroundColor Green
"

exit 0
