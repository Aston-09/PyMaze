"""Solvability check — run: python test_solutions.py

Every mission the learner meets before functions are taught is now a plain
script: the System hands them ready-made variables, they store an answer in
another. This file plays each of those missions with a model answer and
asserts the engine accepts it, so a reworded instruction that no longer
matches its own tests fails here instead of in front of a learner.
"""
import os
import sys

os.environ.setdefault("JWT_SECRET_KEY", "x" * 64)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app.main as m                                    # noqa: E402
from app.engine.executor import execute_and_test        # noqa: E402

SOLUTIONS = {
    "alchemist_wards": "can_enter = level >= 5 and has_key",
    "loops_intro": "span = 0\nfor plank in range(1, n + 1):\n    span = span + plank",
    "halls_doors_break": (
        "opened = 0\n"
        "for door in range(1, door_count + 1):\n"
        "    if door == cursed_door:\n"
        "        break\n"
        "    opened = opened + 1"
    ),
    "halls_free_warden": "count = 0\nwhile count < steps_to_door:\n    count = count + 1",
    "caravan_lists": "crate = supplies[position - 1]",
    "satchel_pack": "satchel.append(item)\ncrate_count = len(satchel)",
    "satchel_middle": "middle = supplies[1:-1]",
    "grimoire_dicts": 'incantation = grimoire.get(spell_name, "Unknown Spell")',
    "catalogue_lookup": "book_knows = name in grimoire",
    "catalogue_distinct": "distinct_count = len(set(grimoire.values()))",
    "riddle_strings": 'name = runes[:4]\nopening_words = f"The gate opens for {name}."',
    "loom_shout": 'shouted = word.upper() + "!"',
    "loom_titlecard": 'first = full_name.split()[0]\ntitle_card = f"{first} the {rank}"',
}


def main() -> None:
    failures = []

    # The point of the rework: nothing the learner meets before chapter 7
    # may ask them to write `def`. The exceptions are chapter 7 itself, the
    # optional DSA boss, and the authoring example in docs.
    MAY_USE_DEF = {"dragon_trial", "merchant_ledger"}
    for cid, ch in m.CHALLENGES.items():
        if (ch.test_type == "function" and cid not in MAY_USE_DEF
                and not cid.startswith(("spellbook_", "enchanter_", "workshop_"))):
            failures.append(f"{cid}: still a `function` challenge before functions are taught")

    for cid, code in SOLUTIONS.items():
        ch = m.CHALLENGES.get(cid)
        if not ch:
            failures.append(f"{cid}: challenge missing")
            continue
        result = execute_and_test(
            user_code=code,
            test_type=ch.test_type,
            validation_tests=ch.validation_tests,
            function_name=ch.function_name,
            input_variable=ch.input_variable,
            output_variable=ch.output_variable,
            expected_variables=ch.expected_variables,
        )
        if not result.get("success"):
            bad = [t for t in result.get("test_results", []) if not t.get("passed")]
            failures.append(f"{cid}: model answer rejected — {result.get('message')} {bad[:1]}")

    for f in failures:
        print("FAIL:", f)
    assert not failures, f"{len(failures)} solvability failures"
    print(f"solutions OK ({len(SOLUTIONS)} missions)")


if __name__ == "__main__":
    main()
