"""
PowerShell Executor Service

Handles execution of PowerShell scripts for M365 CIS compliance scanning.
"""

import asyncio
import json
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Any, Sequence
from datetime import datetime

from app.features.core.sqlalchemy_imports import *

logger = get_logger(__name__)


class PowerShellExecutorService:
    """
    Service for executing PowerShell scripts in a controlled manner.

    Handles subprocess management, parameter passing, output parsing,
    and error handling for PowerShell script execution.
    """

    def __init__(self):
        """Initialize PowerShell executor."""
        self.script_base_path = Path(__file__).parent.parent / "CIS_Microsoft_365_Foundations_Benchmark_v5.0.0"
        self.start_checks_script = self.script_base_path / "Start-Checks.ps1"

    async def execute_start_checks(
        self,
        auth_params: Dict[str, str],
        scan_id: str,
        progress_callback_url: Optional[str] = None,
        tech: str = "M365",
        output_format: str = "json",
        check_ids: Optional[List[str]] = None,
        l1_only: bool = False,
        timeout: int = 3600
    ) -> Dict[str, Any]:
        """
        Execute Start-Checks.ps1 PowerShell script.

        Args:
            auth_params: Authentication parameters (TenantId, ClientId, ClientSecret, etc.)
            scan_id: Unique scan identifier for grouping results
            progress_callback_url: URL to POST progress updates to
            tech: Technology type (M365, Azure, AWS, etc.)
            output_format: Output format (json or csv)
            check_ids: Optional list of specific check IDs to run
            l1_only: Run only Level 1 checks
            timeout: Maximum execution time in seconds (default: 1 hour)

        Returns:
            Dictionary with execution results

        Raises:
            RuntimeError: If PowerShell execution fails
            FileNotFoundError: If Start-Checks.ps1 not found
            asyncio.TimeoutError: If execution exceeds timeout
        """
        logger.info(
            "Starting PowerShell compliance scan",
            scan_id=scan_id,
            tech=tech,
            l1_only=l1_only,
            has_callback=bool(progress_callback_url)
        )

        # Verify script exists
        if not self.start_checks_script.exists():
            raise FileNotFoundError(f"Start-Checks.ps1 not found at {self.start_checks_script}")

        # Build PowerShell command and capture results via temporary workspace
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                command = self._build_powershell_command(
                    temp_dir=temp_dir,
                    auth_params=auth_params,
                    scan_id=scan_id,
                    tech=tech,
                    output_format=output_format,
                    check_ids=check_ids,
                    l1_only=l1_only,
                    progress_callback_url=progress_callback_url
                )

                logger.debug("PowerShell command prepared", command=command)

                # Execute PowerShell script asynchronously
                result = await self._execute_powershell_async(command, timeout)

                # Parse output
                parsed_result = await self._parse_execution_result(
                    result=result,
                    scan_id=scan_id
                )

            logger.info(
                "PowerShell scan completed",
                scan_id=scan_id,
                status=parsed_result.get("status"),
                checks_executed=parsed_result.get("checks_executed", 0),
                error=parsed_result.get("error")
            )

            return parsed_result

        except asyncio.TimeoutError:
            logger.error("PowerShell execution timeout", scan_id=scan_id, timeout=timeout)
            raise
        except Exception as e:
            logger.error("PowerShell execution failed", scan_id=scan_id, error=str(e))
            raise RuntimeError(f"PowerShell execution failed: {str(e)}")

    def _escape_ps_string(self, value: str) -> str:
        """Escape string for use inside PowerShell double quotes."""
        return value.replace("`", "``").replace('"', '`"')

    def _build_powershell_command(
        self,
        temp_dir: str,
        auth_params: Dict[str, str],
        scan_id: str,
        tech: str,
        output_format: str,
        check_ids: Optional[List[str]],
        l1_only: bool,
        progress_callback_url: Optional[str],
        output_path: Optional[str] = None,
    ) -> Sequence[str]:
        """
        Build PowerShell command by generating a temporary runner script.
        """
        import base64

        temp_dir_path = Path(temp_dir)
        auth_path = temp_dir_path / "auth_params.json"
        runner_script = temp_dir_path / "run_scan.ps1"

        # Handle certificate PFX if provided as base64
        if "CertificatePfxBase64" in auth_params:
            try:
                # Decode base64 PFX and write to temp file
                pfx_base64 = auth_params.pop("CertificatePfxBase64")
                pfx_bytes = base64.b64decode(pfx_base64)
                cert_path = temp_dir_path / "cert.pfx"
                cert_path.write_bytes(pfx_bytes)

                # Replace base64 with file path for PowerShell
                auth_params["CertificatePath"] = str(cert_path)

                logger.info("Certificate PFX decoded and saved to temp file", path=str(cert_path))
            except Exception as e:
                logger.error("Failed to decode certificate PFX", error=str(e))
                raise RuntimeError(f"Failed to process certificate: {str(e)}")

        # Write auth params to JSON file if provided
        has_auth_params = bool(auth_params)
        if has_auth_params:
            auth_path.write_text(json.dumps(auth_params), encoding="utf-8")

        lines = [
            "$ErrorActionPreference = 'Stop'",
        ]

        # Only load and pass auth params if they exist
        if has_auth_params:
            lines.extend([
                f"$authParams = Get-Content -Raw -Path \"{self._escape_ps_string(str(auth_path))}\" | ConvertFrom-Json",
                "",
                "# Build AuthParams hashtable from JSON",
                "$authHash = @{}",
                "foreach ($property in $authParams.PSObject.Properties) {",
                "    # Only add non-null values to auth hash",
                "    if ($null -ne $property.Value -and $property.Value -ne '') {",
                "        $authHash[$property.Name] = $property.Value",
                "    }",
                "}",
                "",
            ])

        # Build Start-Checks parameters
        lines.append("# Build Start-Checks parameters")
        lines.append("$params = @{")
        lines.append(f"    Tech = \"{self._escape_ps_string(tech)}\"")

        # Only include AuthParams if we have them
        if has_auth_params:
            lines.append("    AuthParams = $authHash")

        if output_path:
            lines.append(f"    OutputPath = \"{self._escape_ps_string(output_path)}\"")

        lines.append(f"    OutputFormat = \"{self._escape_ps_string(output_format)}\"")
        lines.append("}")

        if check_ids:
            escaped_ids = [f"\"{self._escape_ps_string(cid)}\"" for cid in check_ids]
            lines.append(f"$params.CheckIds = @({', '.join(escaped_ids)})")

        if l1_only:
            lines.append("$params.L1Only = $true")

        if progress_callback_url:
            lines.append(f"$params.ProgressCallbackUrl = \"{self._escape_ps_string(progress_callback_url)}\"")

        # Always pass ScanId for progress tracking
        lines.append(f"$params.ScanId = \"{self._escape_ps_string(scan_id)}\"")

        # Execute Start-Checks.ps1 - it now outputs JSON directly to stdout via Write-Output
        # No need to capture/serialize - just let the output pass through
        lines.append(f"& \"{self._escape_ps_string(str(self.start_checks_script))}\" @params")
        lines.append("exit $LASTEXITCODE")

        runner_script.write_text("\n".join(lines), encoding="utf-8")

        return [
            "pwsh",
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", str(runner_script)
        ]

    async def _execute_powershell_async(
        self,
        command: Sequence[str],
        timeout: int
    ) -> subprocess.CompletedProcess:
        """
        Execute PowerShell command asynchronously using native async subprocess.

        Args:
            command: PowerShell command to execute
            timeout: Timeout in seconds

        Returns:
            CompletedProcess result

        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
        """
        logger.debug("Executing PowerShell command", timeout=timeout, command=command)

        try:
            # Prepare environment with timeout configuration
            # CRITICAL: Pass full environment to subprocess so PowerShell scripts can:
            # 1. Access POWERSHELL_HTTPCLIENT_TIMEOUT_SEC for HTTP client timeout
            # 2. Inherit PATH for module discovery
            # 3. Get WSL/Linux environment variables for network configuration
            env = os.environ.copy()

            # Explicitly set PowerShell HTTP timeout to 5 minutes (300 seconds)
            # This is read by Connect-M365.ps1 and should be respected by some modules
            env['POWERSHELL_HTTPCLIENT_TIMEOUT_SEC'] = '300'

            logger.debug(
                "PowerShell subprocess environment prepared",
                has_path=bool(env.get('PATH')),
                http_timeout=env.get('POWERSHELL_HTTPCLIENT_TIMEOUT_SEC'),
                env_var_count=len(env)
            )

            # Use native async subprocess instead of run_in_executor
            # This avoids threading issues that can cause slow DNS/network in WSL2
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env  # Pass full environment to subprocess
            )

            # Wait for process with timeout
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            # Decode output
            stdout = stdout_bytes.decode('utf-8') if stdout_bytes else ""
            stderr = stderr_bytes.decode('utf-8') if stderr_bytes else ""

            # Create CompletedProcess-like object for compatibility
            result = subprocess.CompletedProcess(
                args=list(command),
                returncode=process.returncode,
                stdout=stdout,
                stderr=stderr
            )

            # Log stdout/stderr
            if result.stdout:
                logger.info("PowerShell stdout", output=result.stdout[:2000], output_length=len(result.stdout))
            if result.stderr:
                logger.warning("PowerShell stderr", error=result.stderr[:2000])

            if result.returncode != 0:
                raise RuntimeError(f"PowerShell exited with code {result.returncode}: {result.stderr}")

            return result

        except asyncio.TimeoutError:
            logger.error("PowerShell execution timeout", timeout=timeout)
            # Try to kill the process if it's still running
            try:
                process.kill()
                await process.wait()
            except:
                pass
            raise

    async def _parse_execution_result(
        self,
        result: subprocess.CompletedProcess,
        scan_id: str
    ) -> Dict[str, Any]:
        """
        Parse PowerShell execution result and output file.

        Args:
            result: Subprocess completed process
            output_path: Path to output JSON file
            scan_id: Scan ID for tracking

        Returns:
            Parsed result dictionary with status and results
        """
        parsed = {
            "scan_id": scan_id,
            "status": "unknown",
            "checks_executed": 0,
            "results": [],
            "output_path": None,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

        def _parse_stdout_json(stdout_text: str) -> Optional[Dict[str, Any]]:
            """
            Extract JSON from stdout that may contain ANSI codes and mixed output.

            PowerShell Write-Information output goes to Information stream (not captured by Python),
            but stdout may still contain ANSI escape codes. This function:
            1. Removes ANSI escape codes
            2. Finds JSON object (starts with { at beginning of line)
            3. Extracts complete JSON with balanced braces
            """
            if not stdout_text:
                return None

            import re

            # Remove ANSI escape codes
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_text = ansi_escape.sub('', stdout_text)

            # Find JSON object - look for first '{' at start of line and extract until matching '}'
            json_start = -1
            json_end = -1
            brace_count = 0

            for i, char in enumerate(clean_text):
                if char == '{' and json_start == -1:
                    # Check if this is at the start of a line (preceded by newline or start of string)
                    if i == 0 or clean_text[i-1] == '\n':
                        json_start = i
                        brace_count = 1
                elif json_start != -1:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

            if json_start != -1 and json_end != -1:
                json_str = clean_text[json_start:json_end]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(
                        "Found JSON-like structure but failed to parse",
                        scan_id=scan_id,
                        error=str(e),
                        json_preview=json_str[:200]
                    )
                    # Continue to fallback

            # Fallback: Try line-by-line parsing from end (old behavior)
            lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
            for line in reversed(lines):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

            return None

        stdout_payload = _parse_stdout_json(result.stdout)

        if stdout_payload and isinstance(stdout_payload, dict):
            parsed["metadata"] = stdout_payload
            parsed["status"] = stdout_payload.get("Status", parsed["status"])
            parsed["checks_executed"] = stdout_payload.get("ChecksExecuted", parsed["checks_executed"])
            parsed["results"] = stdout_payload.get("Results", parsed["results"])
            parsed["output_path"] = stdout_payload.get("OutputPath")
            error_msg = stdout_payload.get("Error")
            if error_msg:
                parsed["error"] = error_msg
                logger.error(
                    "PowerShell scan returned error payload",
                    scan_id=scan_id,
                    error=error_msg
                )
            else:
                logger.info(
                    "Parsed PowerShell stdout payload",
                    scan_id=scan_id,
                    status=parsed["status"],
                    checks=parsed["checks_executed"]
                )
        elif stdout_payload and isinstance(stdout_payload, list):
            # PowerShell returned a list (likely the Results array directly)
            # This can happen if ConvertTo-Json serializes an array
            logger.warning(
                "PowerShell output is a list instead of dict",
                scan_id=scan_id,
                list_length=len(stdout_payload),
                stdout_preview=result.stdout[:500]
            )
            # Treat the list as the Results array
            parsed["results"] = stdout_payload
            parsed["checks_executed"] = len(stdout_payload)
            parsed["status"] = "Success"  # Assume success if we got results
            logger.info(
                "Parsed PowerShell list payload as results",
                scan_id=scan_id,
                results_count=len(stdout_payload)
            )
        else:
            parsed["status"] = "error"
            parsed["error"] = "PowerShell output did not include JSON payload"
            logger.error(
                "Failed to parse PowerShell stdout payload",
                scan_id=scan_id,
                stdout_preview=result.stdout[:500]
            )

        return parsed

    async def test_powershell_environment(self) -> Dict[str, Any]:
        """
        Test PowerShell environment and module availability.

        Returns:
            Dictionary with test results
        """
        logger.info("Testing PowerShell environment")

        test_command = """
pwsh -NoLogo -NoProfile -Command "
    Write-Output 'PowerShell Version:'
    $PSVersionTable.PSVersion | ConvertTo-Json

    Write-Output ''
    Write-Output 'Available Modules:'
    $modules = @('Microsoft.Graph', 'ExchangeOnlineManagement', 'MicrosoftTeams', 'PnP.PowerShell', 'MicrosoftPowerBIMgmt')
    $moduleStatus = @{}
    foreach ($module in $modules) {
        $installed = Get-Module -ListAvailable -Name $module | Select-Object -First 1
        $moduleStatus[$module] = if ($installed) { $installed.Version.ToString() } else { 'NOT INSTALLED' }
    }
    $moduleStatus | ConvertTo-Json
"
"""

        try:
            result = subprocess.run(
                test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }

        except Exception as e:
            logger.error("PowerShell environment test failed", error=str(e))
            return {
                "success": False,
                "output": None,
                "error": str(e)
            }

    async def test_m365_connection(
        self,
        auth_params: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Test M365 connection with provided credentials.

        Args:
            auth_params: Authentication parameters

        Returns:
            Connection test result
        """
        logger.info("Testing M365 connection", tenant_id=auth_params.get("TenantId"))

        # Build simple connection test script
        auth_params_ps = "@{"
        for key, value in auth_params.items():
            escaped_value = str(value).replace("'", "''")
            auth_params_ps += f"{key}='{escaped_value}'; "
        auth_params_ps = auth_params_ps.rstrip("; ") + "}"

        test_script = textwrap.dedent(f"""
            try {{
                $authParams = {auth_params_ps}

                if ($authParams.ClientId -and $authParams.ClientSecret) {{
                    $secureSecret = ConvertTo-SecureString $authParams.ClientSecret -AsPlainText -Force
                    $credential = New-Object System.Management.Automation.PSCredential($authParams.ClientId, $secureSecret)
                    Connect-MgGraph -TenantId $authParams.TenantId -ClientSecretCredential $credential -NoWelcome
                    Write-Output 'SUCCESS: Connected to Microsoft Graph'
                    Disconnect-MgGraph
                }} else {{
                    Write-Output 'ERROR: Missing ClientId or ClientSecret'
                    exit 1
                }}
            }} catch {{
                Write-Output "ERROR: $($_.Exception.Message)"
                exit 1
            }}
        """).strip()

        command = [
            "pwsh",
            "-NoLogo",
            "-NoProfile",
            "-Command",
            test_script
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            success = result.returncode == 0 and "SUCCESS" in stdout
            message = stdout if success else (stdout or stderr)

            return {
                "success": success,
                "message": message,
                "tested_at": datetime.now()
            }

        except subprocess.TimeoutExpired:
            logger.error("M365 connection test timeout")
            return {
                "success": False,
                "message": "Connection test timed out after 60 seconds",
                "tested_at": datetime.now()
            }
        except Exception as e:
            logger.error("M365 connection test failed", error=str(e))
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "tested_at": datetime.now()
            }
