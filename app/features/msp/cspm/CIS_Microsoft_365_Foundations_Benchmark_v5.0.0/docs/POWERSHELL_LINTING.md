# PowerShell Linting and Code Quality

This project includes comprehensive PowerShell linting and validation tools to ensure code quality and catch errors early in the development process.

## Available Tools

### 1. Test-PowerShellLinting.ps1 - Comprehensive Analysis
**Purpose:** Full-featured PowerShell code analysis with detailed reporting

**Usage:**
```powershell
# Full analysis with detailed output
.\Test-PowerShellLinting.ps1 -Path "checks" -Detailed

# Errors only (fast check)
.\Test-PowerShellLinting.ps1 -Path "checks" -Severity @("Error")

# Specific file analysis
.\Test-PowerShellLinting.ps1 -Path "checks\L1\specific_file.ps1" -Detailed

# Include warnings and errors
.\Test-PowerShellLinting.ps1 -Path "checks" -Severity @("Error", "Warning")
```

**Features:**
- ✅ Syntax validation (catches parse errors)
- ✅ PSScriptAnalyzer integration (best practices)
- ✅ Colored output with severity indicators
- ✅ Detailed reporting with line numbers
- ✅ Summary statistics
- ✅ Exit codes for CI/CD integration

### 2. Test-PowerShellCI.ps1 - CI/CD Integration
**Purpose:** Lightweight validation suitable for automated pipelines

**Usage:**
```powershell
# Standard CI validation
.\Test-PowerShellCI.ps1 -ChecksPath "checks"

# Strict mode (fail on warnings)
.\Test-PowerShellCI.ps1 -ChecksPath "checks" -FailOnWarnings
```

**Features:**
- ⚡ Fast execution
- 🚦 Clear pass/fail indication
- 📊 Summary reporting
- 🔧 Configurable warning sensitivity
- 💾 Minimal output for logs

## VS Code Integration

### Tasks Available (Ctrl+Shift+P → "Tasks: Run Task")

1. **PowerShell Lint - Full Analysis**
   - Comprehensive analysis of all check files
   - Detailed output with problem matching

2. **PowerShell Lint - CI Mode** 
   - Quick validation suitable for pre-commit checks
   - Fast feedback on critical issues

3. **PowerShell Lint - Errors Only**
   - Focus on syntax errors and critical issues only
   - Good for rapid development cycles

4. **PowerShell Lint - Single File**
   - Analyze currently open file
   - Perfect for focused development

### Problem Matcher Integration
The VS Code tasks include problem matchers that automatically parse linting output and display issues in the Problems panel.

## PSScriptAnalyzer Rules

### Currently Enforced Rules
- **Syntax Errors:** All syntax issues are treated as blocking errors
- **Critical Issues:** Security and functionality problems
- **Best Practice Warnings:** Code style and maintainability

### Common Issues Found
1. **Null Comparison Order:** `$null should be on left side`
   ```powershell
   # Bad
   if ($variable -eq $null) { }
   
   # Good  
   if ($null -eq $variable) { }
   ```

2. **Unused Variables:** Variables assigned but never used
3. **Command Resolution:** Unknown cmdlets or functions
4. **Parameter Issues:** Incorrect parameter usage

## CI/CD Integration

### Exit Codes
- **0:** All checks passed
- **1:** Warnings found (fails if -FailOnWarnings enabled)  
- **2:** Syntax errors or critical issues found

### GitHub Actions Example
```yaml
- name: PowerShell Linting
  run: |
    pwsh -ExecutionPolicy Bypass -File ./Test-PowerShellCI.ps1 -ChecksPath "checks"
```

### Azure DevOps Example
```yaml
- task: PowerShell@2
  displayName: 'PowerShell Code Quality Check'
  inputs:
    targetType: 'filePath'
    filePath: './Test-PowerShellCI.ps1'
    arguments: '-ChecksPath "checks"'
    failOnStderr: true
```

## Configuration

### Customizing Severity Levels
You can adjust which issues cause failures:

```powershell
# Only fail on errors, ignore warnings
.\Test-PowerShellLinting.ps1 -Severity @("Error")

# Include informational messages  
.\Test-PowerShellLinting.ps1 -Severity @("Error", "Warning", "Information")
```

### Auto-Fix Capabilities
The linting script includes hooks for auto-fixing common issues:

```powershell
# Future: Auto-fix mode
.\Test-PowerShellLinting.ps1 -Fix
```

## Development Workflow

### Recommended Process
1. **Write PowerShell code** for compliance checks
2. **Run local linting** using VS Code tasks or command line
3. **Fix any issues** identified by the linter
4. **Commit code** - CI will validate automatically  
5. **Monitor CI results** in your pipeline

### Pre-Commit Hook
Consider adding a pre-commit hook:
```bash
#!/bin/sh
pwsh -ExecutionPolicy Bypass -File ./Test-PowerShellCI.ps1 -ChecksPath "checks"
```

## Benefits

### For Developers
- 🐛 **Catch errors early** - before runtime
- 📚 **Learn best practices** - through warning messages  
- ⚡ **Fast feedback** - integrated into development workflow
- 🎯 **Focused fixes** - precise line number reporting

### For CI/CD
- 🚦 **Automated quality gates** - prevent bad code from merging
- 📈 **Quality metrics** - track code quality over time
- 🔄 **Consistent standards** - enforce coding standards across team
- ⚡ **Fast execution** - minimal impact on pipeline time

### For Production
- 🛡️ **Reduced runtime errors** - catch issues before deployment
- 📊 **Better reliability** - higher quality PowerShell scripts
- 🔧 **Easier maintenance** - consistent, well-formatted code
- 📖 **Self-documenting** - adherence to PowerShell best practices

## Status

✅ **Implemented:** Full syntax validation and PSScriptAnalyzer integration  
✅ **Implemented:** VS Code task integration  
✅ **Implemented:** CI/CD ready scripts with proper exit codes  
🚧 **In Progress:** Auto-fix capabilities for common issues  
📋 **Planned:** Custom rule configuration and team-specific standards