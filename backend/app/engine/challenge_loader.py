"""
Challenge Loader

Scans the challenges/ directory, loads all .json files,
and indexes them by challenge_id for fast lookup.
"""
import os
import re
import json
import logging
from typing import Dict, List
from pydantic import ValidationError
from app.models.challenge import ChallengeDefinition

log = logging.getLogger(__name__)


def load_all_challenges(challenges_dir: str) -> Dict[str, ChallengeDefinition]:
    """Discover and load all challenge JSON files.

    A malformed challenge file is skipped with a logged error rather than
    taking down the whole server at import time.
    Returns a dict keyed by challenge_id.
    """
    challenges: Dict[str, ChallengeDefinition] = {}

    if not os.path.isdir(challenges_dir):
        log.warning("Challenges directory not found: %s", challenges_dir)
        return challenges

    for filename in sorted(os.listdir(challenges_dir)):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(challenges_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            challenge = ChallengeDefinition(**data)
        except (json.JSONDecodeError, ValidationError, OSError) as exc:
            log.error("Skipping invalid challenge file %s: %s", filename, exc)
            continue

        if challenge.challenge_id in challenges:
            log.warning(
                "Duplicate challenge_id '%s' in %s — overwriting the earlier one.",
                challenge.challenge_id, filename,
            )
        challenges[challenge.challenge_id] = challenge

    return challenges


def validate_challenges(challenges: Dict[str, ChallengeDefinition]) -> List[str]:
    """Return a list of authoring problems found in the loaded challenges.

    These are content bugs that silently produce unwinnable challenges, so we
    surface them at startup instead of letting a learner grind against an
    impossible test.
    """
    problems: List[str] = []

    for cid, ch in challenges.items():
        if ch.test_type == "script_variable":
            if not ch.output_variable:
                problems.append(f"{cid}: script_variable challenge has no output_variable")

            # The killer bug: starter code that assigns the injected input
            # variable shadows every test case after the first.
            if ch.input_variable and _assigns(ch.starting_code, ch.input_variable):
                problems.append(
                    f"{cid}: starting_code assigns '{ch.input_variable}', which is "
                    f"injected per test case — every test but the first will fail. "
                    f"Remove the assignment from starting_code."
                )

        elif ch.test_type == "script_output":
            if ch.input_variable and _assigns(ch.starting_code, ch.input_variable):
                problems.append(
                    f"{cid}: starting_code assigns '{ch.input_variable}', which is "
                    f"injected per test case — every test but the first will fail. "
                    f"Remove the assignment from starting_code."
                )

        elif ch.test_type == "function":
            if not ch.function_name:
                problems.append(f"{cid}: function challenge has no function_name")

        elif ch.test_type == "variables":
            if not ch.expected_variables:
                problems.append(f"{cid}: variables challenge has no expected_variables")

        else:
            problems.append(f"{cid}: unknown test_type '{ch.test_type}'")

        if ch.test_type in ("function", "script_variable", "script_output") and not ch.validation_tests:
            problems.append(f"{cid}: no validation_tests defined")

    return problems


def _assigns(code: str, name: str) -> bool:
    """True if `code` contains a top-level assignment to `name`."""
    pattern = rf"^{re.escape(name)}\s*(?::[^=]+)?=(?!=)"
    return re.search(pattern, code, re.MULTILINE) is not None
