"""
Scoring Engine

Analyzes user-submitted code to award bonus programmer stats
(Intelligence, Wisdom, Dexterity) beyond the base XP/Gold rewards.
"""
import re
from typing import Dict, Any


def score_code(user_code: str, test_results: Dict[str, Any]) -> Dict[str, int]:
    """Analyze the user's code and return bonus stat awards.

    Returns dict with keys: int_bonus, wis_bonus, dex_bonus
    """
    int_bonus = 0
    wis_bonus = 0
    dex_bonus = 0

    lines = [l for l in user_code.strip().split("\n") if l.strip() and not l.strip().startswith("#")]

    if not lines:
        return {"int_bonus": 0, "wis_bonus": 0, "dex_bonus": 0}

    # --- Intelligence: correct syntax and logic ---
    if test_results.get("success"):
        int_bonus += 3  # Base for passing

    # --- Wisdom: meaningful variable names ---
    # Heuristic: find all assignments, check if var names are descriptive
    assignments = re.findall(r"^(\w+)\s*=", user_code, re.MULTILINE)
    good_names = 0
    for name in assignments:
        if name.startswith("_"):
            continue
        # Good name: at least 3 chars, uses snake_case or descriptive words
        if len(name) >= 3 and (name.islower() or "_" in name):
            good_names += 1

    if assignments and good_names >= len(assignments) * 0.7:
        wis_bonus += 2

    # --- Dexterity: concise code ---
    # Fewer lines = more dexterous (relative to a generous threshold)
    if len(lines) <= 10:
        dex_bonus += 1
    if len(lines) <= 5:
        dex_bonus += 1

    # Check for list comprehensions (advanced conciseness)
    if re.search(r"\[.+\bfor\b.+\bin\b.+\]", user_code):
        dex_bonus += 2

    return {
        "int_bonus": int_bonus,
        "wis_bonus": wis_bonus,
        "dex_bonus": dex_bonus,
    }
