"""
Code Executor

Runs learner-submitted Python code out-of-process and tests it against a
challenge's validation rules.

The actual execution happens in sandbox.py, launched as a short-lived
subprocess. That boundary is what makes `while True:` a failed submission
instead of a dead API server.

Supports four test types:
  - "function":        learner defines a function, engine calls it with inputs
  - "script_variable": engine injects input vars, runs script, checks output var
  - "variables":       learner defines variables, engine checks names/types
  - "script_output":   engine injects input vars, runs script, checks stdout print output
"""
import os
import sys
import json
import subprocess
from typing import Dict, Any, List, Optional

SANDBOX_SCRIPT = os.path.join(os.path.dirname(__file__), "sandbox.py")

# Wall-clock budget for a single submission. Generous enough for a naive
# O(n^2) DSA answer, short enough that a runaway loop fails fast.
DEFAULT_TIMEOUT_SECONDS = 5.0


def execute_and_test(
    user_code: str,
    test_type: str,
    validation_tests: List[Dict[str, Any]],
    function_name: Optional[str] = None,
    input_variable: Optional[str] = None,
    output_variable: Optional[str] = None,
    expected_variables: Optional[Dict[str, str]] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Execute learner code against test cases.

    Always returns a dict with: success, message, output, test_results.
    Never raises — a broken submission is a game event, not a server error.
    """
    payload = {
        "user_code": user_code,
        "test_type": test_type,
        "validation_tests": validation_tests or [],
        "function_name": function_name,
        "input_variable": input_variable,
        "output_variable": output_variable,
        "expected_variables": expected_variables or {},
    }

    try:
        proc = subprocess.run(
            [sys.executable, SANDBOX_SCRIPT],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            # Game copy is full of emoji; never fall back to the Windows
            # locale codepage (cp1252), which cannot encode them.
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            # Don't inherit the server's cwd-relative import path.
            env={
                **os.environ,
                "PYTHONPATH": "",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "utf-8",
            },
        )
    except subprocess.TimeoutExpired:
        return _failure(
            f"Your code ran longer than {timeout:g} seconds and was stopped. "
            "Check for an infinite loop."
        )
    except Exception as exc:  # sandbox could not be launched at all
        return _failure(f"Could not start the code runner: {exc}")

    if proc.returncode != 0 and not proc.stdout.strip():
        # Hard crash inside the sandbox (segfault, MemoryError, os._exit...).
        detail = (proc.stderr or "").strip().splitlines()
        return _failure(
            "Your code crashed the runner.",
            output=detail[-1] if detail else "",
        )

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return _failure(
            "The code runner returned an unreadable result.",
            output=(proc.stderr or proc.stdout or "")[:2000],
        )


def _failure(message: str, output: str = "") -> Dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "output": output,
        "test_results": [],
    }
