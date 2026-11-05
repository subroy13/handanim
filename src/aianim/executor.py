"""Subprocess execution engine with timeout and error capture for generated animations."""

import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExecutionResult:
    """Outcome of running a generated handanim script."""

    success: bool
    stdout: str
    stderr: str
    returncode: int
    output_exists: bool
    execution_time: float
    error_summary: str = ""


class CodeExecutor:
    """Executes generated Python code in an isolated subprocess."""

    def __init__(self, default_timeout: float = 45.0):
        self.default_timeout = default_timeout

    def execute(
        self,
        code: str,
        expected_output: str | None = None,
        timeout: float | None = None,
        working_dir: str | Path | None = None,
    ) -> ExecutionResult:
        """Execute Python code string in a subprocess and verify output creation.

        Args:
            code: Full Python source code.
            expected_output: Optional path to output media file (e.g. .mp4, .svg) to verify.
            timeout: Subprocess timeout in seconds. Defaults to self.default_timeout.
            working_dir: Working directory for execution. Defaults to repository root.

        Returns:
            ExecutionResult containing execution status, logs, and error details.
        """
        cwd = str(working_dir or Path.cwd())
        timeout_val = timeout or self.default_timeout

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(code)

        start_time = time.time()
        try:
            # Set PYTHONPATH so the subprocess can import handanim from src/
            env = os.environ.copy()
            repo_src = str(Path(__file__).resolve().parent.parent)
            existing_pp = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{repo_src}:{existing_pp}" if existing_pp else repo_src

            proc = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout_val,
                cwd=cwd,
                env=env,
            )
            elapsed = time.time() - start_time
            output_exists = (
                os.path.exists(expected_output) and os.path.getsize(expected_output) > 0 if expected_output else True
            )

            success = proc.returncode == 0 and output_exists
            error_summary = ""
            if proc.returncode != 0:
                error_summary = proc.stderr.strip()
            elif expected_output and not output_exists:
                error_summary = (
                    f"Script completed with code 0 but expected output file '{expected_output}' was not created."
                )

            return ExecutionResult(
                success=success,
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
                output_exists=output_exists,
                execution_time=elapsed,
                error_summary=error_summary,
            )

        except subprocess.TimeoutExpired as e:
            elapsed = time.time() - start_time
            return ExecutionResult(
                success=False,
                stdout=e.stdout or "" if isinstance(e.stdout, str) else "",
                stderr=e.stderr or "" if isinstance(e.stderr, str) else "",
                returncode=-1,
                output_exists=False,
                execution_time=elapsed,
                error_summary=f"Execution timed out after {timeout_val} seconds.",
            )
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
