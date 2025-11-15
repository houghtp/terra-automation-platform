#!/bin/bash
#
# Install PowerShell Core and M365 modules on WSL2/Debian for local development
#
# Run this script with: bash scripts/install_powershell_local.sh
#

set -e  # Exit on error

echo "======================================================================"
echo "Installing PowerShell Core on WSL2/Debian..."
echo "======================================================================"

# Download Microsoft repository GPG keys
echo ""
echo "Step 1: Downloading Microsoft repository configuration..."
wget -q https://packages.microsoft.com/config/debian/11/packages-microsoft-prod.deb

# Install repository configuration
echo ""
echo "Step 2: Installing Microsoft repository (requires sudo)..."
sudo dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb

# Update package list
echo ""
echo "Step 3: Updating package list..."
sudo apt-get update

# Install PowerShell
echo ""
echo "Step 4: Installing PowerShell Core (requires sudo)..."
sudo apt-get install -y powershell

# Verify PowerShell installation
echo ""
echo "Step 5: Verifying PowerShell installation..."
pwsh --version

echo ""
echo "======================================================================"
echo "PowerShell Core installed successfully!"
echo "======================================================================"

# Now install PowerShell modules
echo ""
echo "======================================================================"
echo "Installing PowerShell modules for M365 CIS compliance scanning..."
echo "======================================================================"

# Note: Set-ExecutionPolicy is not needed on Linux/WSL - it's Windows-only

# Microsoft Graph SDK - Core authentication and API access for Entra ID, Users, Groups, Security
echo ""
echo "[1/5] Installing Microsoft.Graph..."
pwsh -NoLogo -NoProfile -Command "Install-Module Microsoft.Graph -Scope CurrentUser -Force -AllowClobber -SkipPublisherCheck -ErrorAction Stop"

# Exchange Online Management - Exchange mailbox, security, and compliance settings
echo ""
echo "[2/5] Installing ExchangeOnlineManagement..."
pwsh -NoLogo -NoProfile -Command "Install-Module ExchangeOnlineManagement -Scope CurrentUser -Force -AllowClobber -SkipPublisherCheck -ErrorAction Stop"

# Microsoft Teams - Teams policies, settings, and configurations
echo ""
echo "[3/5] Installing MicrosoftTeams..."
pwsh -NoLogo -NoProfile -Command "Install-Module MicrosoftTeams -Scope CurrentUser -Force -AllowClobber -SkipPublisherCheck -ErrorAction Stop"

# PnP PowerShell - SharePoint Online sites, libraries, and configurations
echo ""
echo "[4/5] Installing PnP.PowerShell..."
pwsh -NoLogo -NoProfile -Command "Install-Module PnP.PowerShell -Scope CurrentUser -Force -AllowClobber -SkipPublisherCheck -ErrorAction Stop"

# Power BI Management - Power BI tenant settings and admin APIs (includes Fabric)
echo ""
echo "[5/5] Installing MicrosoftPowerBIMgmt..."
pwsh -NoLogo -NoProfile -Command "Install-Module MicrosoftPowerBIMgmt -Scope CurrentUser -Force -AllowClobber -SkipPublisherCheck -ErrorAction Stop"

echo ""
echo "======================================================================"
echo "PowerShell modules installation completed successfully!"
echo "======================================================================"

# Verify installations
echo ""
echo "Verifying installed modules..."
pwsh -NoLogo -NoProfile -Command "
    \$modules = @('Microsoft.Graph', 'ExchangeOnlineManagement', 'MicrosoftTeams', 'PnP.PowerShell', 'MicrosoftPowerBIMgmt')
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

echo ""
echo "======================================================================"
echo "Installation complete! You can now use PowerShell with:"
echo "  pwsh"
echo ""
echo "Your VSCode debugger will now be able to execute PowerShell scripts."
echo "======================================================================"

exit 0
