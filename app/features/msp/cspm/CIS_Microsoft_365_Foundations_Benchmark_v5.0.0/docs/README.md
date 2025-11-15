# M365 CIS Compliance Check - File Structure

This directory contains the essential scripts for M365 CIS compliance checking with resolved Microsoft Graph module conflicts.

## Core Scripts

### `SimpleMainScript.ps1` ✅ MAIN PRODUCTION SCRIPT
- **Primary execution script** for M365 compliance checks
- Includes fixed Microsoft Graph module loading (resolves version conflicts)  
- Python integration ready with progress callbacks
- Enhanced authentication with credential prompting and session reuse
- Supports JSON/CSV output formats

### `MainScript.ps1` 
- Legacy version (kept for compatibility)
- Consider migrating to SimpleMainScript.ps1

### `Run-ComplianceChecks.ps1`
- Wrapper script for batch operations

## PowerShell Code Quality

### `Test-PowerShellLinting.ps1` ✅ LINTING TOOL
- Comprehensive PowerShell code analysis using PSScriptAnalyzer
- Validates syntax, style, and best practices
- Detailed reporting with severity levels

### `Test-PowerShellCI.ps1` ✅ CI/CD INTEGRATION  
- Streamlined linting for automated pipelines
- Exit codes for build integration
- Configurable error thresholds

### `POWERSHELL_LINTING.md`
- Documentation for PowerShell linting setup and usage

## Microsoft Graph Reference

### `Graph_Cmdlet_Reference.ps1` ✅ CMDLET MAPPINGS
- **Essential reference** for correct Microsoft Graph cmdlet names
- Resolves module version conflicts (v2.19.0 → v2.30.0)
- Working cmdlet mappings for compliance checks

## Documentation

### `API_PERMISSIONS_REQUIRED.md`
- Microsoft Graph API permissions reference

### `IMPLEMENTATION_SUMMARY.md` 
- Technical implementation details

## Directories

### `checks/`
- Individual compliance check scripts (CIS benchmarks)

### `authentication/`
- Authentication helper modules

### `templates/`
- Script templates and examples

### `logs/` & `results/`
- Output directories for execution logs and results

### `.vscode/`
- VS Code tasks and workspace configuration

## Key Improvements Made

1. ✅ **Resolved Microsoft Graph module conflicts** - All cmdlets now work correctly
2. ✅ **Enhanced authentication** - Smart session detection and credential reuse  
3. ✅ **Comprehensive linting** - PowerShell code quality assurance
4. ✅ **Clean workspace** - Removed 11 diagnostic/temporary scripts
5. ✅ **Production ready** - SimpleMainScript.ps1 is the primary execution engine

## Usage

### Run Compliance Checks
```powershell
.\SimpleMainScript.ps1 -TenantId "your-tenant-id"
```

### PowerShell Linting
```powershell
.\Test-PowerShellLinting.ps1
```

### Check Cmdlet Reference
```powershell
# View working Microsoft Graph cmdlet mappings
Get-Content .\Graph_Cmdlet_Reference.ps1
```