"""
Sandbox Runner — executes untrusted learner code in a throwaway subprocess.

This module is launched as a standalone script by executor.py:

    python sandbox.py   < {json payload on stdin}   > {json result on stdout}

It must NOT import anything from the `app` package, because it runs without
the backend on sys.path.

Isolation model:
  - separate process  → an infinite loop or a segfault cannot take down the API
  - wall-clock timeout → enforced by the parent (executor.py)
  - restricted builtins → no open/exec/eval/compile/input, imports whitelisted
  - captured stdout    → user prints never corrupt the JSON result channel

ponytail: process-level isolation only. A determined learner can still read
files via a whitelisted module or burn CPU until the timeout. That is an
acceptable ceiling for a local single-player game. If PyBe is ever hosted
multi-tenant, replace this with a container/gVisor/nsjail boundary — keep the
same stdin/stdout JSON contract and executor.py will not need to change.
"""
import sys
import io
import json
import builtins
import contextlib

# Modules a learner may legitimately need for challenges up to DSA level.
ALLOWED_IMPORTS = {
    "math", "random", "string", "collections", "itertools",
    "functools", "re", "json", "datetime", "heapq", "bisect", "statistics",
}

# Builtins that hand out filesystem / arbitrary-code access.
BLOCKED_BUILTINS = {
    "open", "exec", "eval", "compile", "input", "__import__",
    "breakpoint", "exit", "quit", "help", "vars", "globals", "memoryview",
}

MAX_OUTPUT_CHARS = 10_000


def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Allow only whitelisted top-level modules."""
    root = name.split(".")[0]
    if root not in ALLOWED_IMPORTS:
        raise ImportError(
            f"Importing '{root}' is not allowed here. "
            f"Available modules: {', '.join(sorted(ALLOWED_IMPORTS))}"
        )
    return __import__(name, globals, locals, fromlist, level)


def _safe_builtins():
    safe = {k: v for k, v in vars(builtins).items() if k not in BLOCKED_BUILTINS}
    safe["__import__"] = _guarded_import
    return safe


def _fresh_globals():
    return {"__builtins__": _safe_builtins(), "__name__": "__main__"}


def _jsonable(value):
    """Coerce a value produced by user code into something json.dumps can emit."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(_jsonable(v) for v in value)
    return repr(value)


def _describe(value):
    """Human-readable rendering for the results console."""
    return value if isinstance(value, str) else repr(value)


# --- Test strategies -------------------------------------------------------

def _test_variables(user_code, expected_variables, validation_tests):
    """The learner defines raw variables; check each name, type and constraint."""
    g = _fresh_globals()
    exec(user_code, g)

    test_results = []
    all_passed = True

    for idx, (var_name, expected_type) in enumerate(expected_variables.items()):
        if var_name not in g:
            all_passed = False
            test_results.append({
                "test_id": idx + 1,
                "input": var_name,
                "expected": f"type: {expected_type}",
                "actual": "not defined",
                "passed": False,
            })
            continue

        actual_val = g[var_name]
        actual_type = type(actual_val).__name__
        # bool is a subclass of int, but "hp = True" is not a valid stat.
        passed = actual_type == expected_type
        all_passed = all_passed and passed
        test_results.append({
            "test_id": idx + 1,
            "input": var_name,
            "expected": f"type: {expected_type}",
            "actual": f"type: {actual_type}, value: {_jsonable(actual_val)!r}",
            "passed": passed,
        })

    for test in validation_tests:
        tid = len(test_results) + 1
        var_name = test.get("variable")
        if not var_name:
            continue

        if var_name not in g:
            all_passed = False
            test_results.append({
                "test_id": tid, "input": var_name,
                "expected": "defined", "actual": "not defined", "passed": False,
            })
            continue

        actual = g[var_name]
        check = test.get("check", "exists")

        # Every branch must set `passed` — a missing assignment here used to
        # leak the previous loop's result and fail correct submissions.
        if check == "min":
            passed = isinstance(actual, (int, float)) and actual >= test["value"]
            entry = {"input": f"{var_name} >= {test['value']}",
                     "expected": f">= {test['value']}", "actual": _describe(_jsonable(actual))}
        elif check == "max":
            passed = isinstance(actual, (int, float)) and actual <= test["value"]
            entry = {"input": f"{var_name} <= {test['value']}",
                     "expected": f"<= {test['value']}", "actual": _describe(_jsonable(actual))}
        elif check == "type":
            passed = type(actual).__name__ == test["value"]
            entry = {"input": f"type({var_name})",
                     "expected": test["value"], "actual": type(actual).__name__}
        elif check == "equals":
            passed = actual == test["value"]
            entry = {"input": var_name,
                     "expected": _describe(test["value"]), "actual": _describe(_jsonable(actual))}
        else:  # "exists"
            passed = True
            entry = {"input": var_name, "expected": "defined", "actual": _describe(_jsonable(actual))}

        all_passed = all_passed and passed
        test_results.append({"test_id": tid, "passed": passed, **entry})

    user_vars = {
        k: _jsonable(v) for k, v in g.items()
        if not k.startswith("_") and not callable(v)
    }

    return {
        "success": all_passed,
        "message": "All variables defined correctly! ⭐" if all_passed
                   else "Some variables are missing or have the wrong type.",
        "test_results": test_results,
        "user_variables": user_vars,
    }


def _call(fn, test_input):
    """Call the learner's function, spreading list inputs as positional args."""
    if isinstance(test_input, list):
        return fn(*test_input)
    return fn(test_input)


def _test_function(user_code, function_name, validation_tests):
    """The learner defines a function; the engine calls it with each input."""
    g = _fresh_globals()
    exec(user_code, g)

    if function_name not in g or not callable(g[function_name]):
        return {
            "success": False,
            "message": f"Function '{function_name}' not found. Did you name it correctly?",
            "test_results": [],
        }

    fn = g[function_name]
    test_results = []
    all_passed = True

    for idx, test in enumerate(validation_tests):
        test_input = test["input"]
        expected = test["expected"]
        entry = {
            "test_id": idx + 1,
            "input": _describe(test_input),
            "expected": _describe(expected),
        }
        try:
            result = _call(fn, test_input)
            passed = result == expected
            entry.update(actual=_describe(_jsonable(result)), passed=passed)
        except Exception as exc:
            passed = False
            entry.update(actual=None, passed=False,
                         error=f"{type(exc).__name__}: {exc}")

        all_passed = all_passed and passed
        test_results.append(entry)

    return {
        "success": all_passed,
        "message": "All tests passed! ⭐" if all_passed
                   else "Some tests failed. Check the results below.",
        "test_results": test_results,
    }


def _test_script_variable(user_code, input_variable, output_variable, validation_tests):
    """The engine injects an input variable, runs the script, reads an output variable.

    The injected value is a real assignment in the script's globals, so learner
    code that reassigns `input_variable` shadows the test case. Challenge
    authors must therefore keep that name out of `starting_code` — validated at
    startup by challenge_loader.validate_challenges().
    """
    test_results = []
    all_passed = True

    for idx, test in enumerate(validation_tests):
        test_input = test["input"]
        expected = test["expected"]
        entry = {
            "test_id": idx + 1,
            "input": f"{input_variable} = {test_input!r}" if input_variable else _describe(test_input),
            "expected": _describe(expected),
        }

        g = _fresh_globals()

        # Mock input() to support standard python input reading
        _inputs = test_input if isinstance(test_input, list) else [test_input] if test_input is not None else []
        _input_iter = iter(_inputs)
        def _mock_input(prompt=""):
            if prompt:
                print(prompt, end="")
            try:
                return str(next(_input_iter))
            except StopIteration:
                raise EOFError("EOF when reading a line")
        g["__builtins__"]["input"] = _mock_input

        if input_variable:
            g[input_variable] = test_input

        try:
            exec(user_code, g)

            if output_variable and output_variable not in g:
                raise NameError(
                    f"Your code never assigned '{output_variable}'."
                )

            result = g.get(output_variable) if output_variable else None
            passed = result == expected
            entry.update(actual=_describe(_jsonable(result)), passed=passed)
        except Exception as exc:
            passed = False
            entry.update(actual=None, passed=False,
                         error=f"{type(exc).__name__}: {exc}")

        all_passed = all_passed and passed
        test_results.append(entry)

    return {
        "success": all_passed,
        "message": "All tests passed! ⭐" if all_passed
                   else "Some tests failed. Check the results below.",
        "test_results": test_results,
    }


def _test_script_output(user_code, input_variable, validation_tests):
    """The engine injects an input variable, runs the script, and compares stdout against expected output."""
    test_results = []
    all_passed = True

    for idx, test in enumerate(validation_tests):
        test_input = test.get("input")
        expected = test.get("expected_output", test.get("expected", ""))
        entry = {
            "test_id": idx + 1,
            "input": f"{input_variable} = {test_input!r}" if input_variable else _describe(test_input),
            "expected": _describe(expected),
        }

        g = _fresh_globals()

        # Mock input() to support standard python input reading
        _inputs = test_input if isinstance(test_input, list) else [test_input] if test_input is not None else []
        _input_iter = iter(_inputs)
        def _mock_input(prompt=""):
            if prompt:
                print(prompt, end="")
            try:
                return str(next(_input_iter))
            except StopIteration:
                raise EOFError("EOF when reading a line")
        g["__builtins__"]["input"] = _mock_input

        if input_variable:
            g[input_variable] = test_input

        captured = io.StringIO()
        try:
            with contextlib.redirect_stdout(captured):
                exec(user_code, g)

            actual_stdout = captured.getvalue()
            passed = (actual_stdout == expected) or (actual_stdout.strip() == str(expected).strip())
            entry.update(actual=_describe(actual_stdout), passed=passed)
        except Exception as exc:
            passed = False
            entry.update(actual=None, passed=False,
                         error=f"{type(exc).__name__}: {exc}")

        all_passed = all_passed and passed
        test_results.append(entry)

    return {
        "success": all_passed,
        "message": "All tests passed! ⭐" if all_passed
                   else "Some tests failed. Check the results below.",
        "test_results": test_results,
    }


STRATEGIES = {
    "variables": lambda p: _test_variables(
        p["user_code"], p.get("expected_variables") or {}, p.get("validation_tests") or []),
    "function": lambda p: _test_function(
        p["user_code"], p.get("function_name"), p.get("validation_tests") or []),
    "script_variable": lambda p: _test_script_variable(
        p["user_code"], p.get("input_variable"), p.get("output_variable"),
        p.get("validation_tests") or []),
    "script_output": lambda p: _test_script_output(
        p["user_code"], p.get("input_variable"), p.get("validation_tests") or []),
}


def run(payload):
    test_type = payload.get("test_type")
    strategy = STRATEGIES.get(test_type)
    if strategy is None:
        return {
            "success": False,
            "message": f"Unknown test_type: {test_type}",
            "output": "",
            "test_results": [],
        }

    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            result = strategy(payload)
    except SyntaxError as exc:
        result = {
            "success": False,
            "message": f"Syntax error on line {exc.lineno}: {exc.msg}",
            "test_results": [],
        }
    except Exception as exc:
        result = {
            "success": False,
            "message": f"{type(exc).__name__}: {exc}",
            "test_results": [],
        }

    output = captured.getvalue()
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n... (output truncated)"
    result["output"] = output
    return result


def main():
    payload = json.loads(sys.stdin.read())
    result = run(payload)
    # Write to the real stdout — user prints were captured above.
    sys.__stdout__.write(json.dumps(result))


if __name__ == "__main__":
    main()
