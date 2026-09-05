"""Content integrity check — run: python test_content.py

Walks the story graph the way the browser does, so an authoring mistake that
would strand a learner mid-chapter fails here instead of in a play session.

Mirrors the client's `toSegments` (frontend/src/components/SceneManager.jsx):
a `background:` naming a character stacks over the current location, while one
naming a place replaces it. Keeping the two in step is the point — if that
rule changes there, change it here too.
"""
import os
import sys

os.environ.setdefault("JWT_SECRET_KEY", "x" * 64)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app.main as m   # noqa: E402

SCENES, CHALLENGES, INTERACTIONS = m.SCENES, m.CHALLENGES, m.INTERACTIONS
_FRAMES = m._art_frame_map()
CHARACTERS = {
    stem for stem, paths in _FRAMES.items()
    if paths and paths[0].startswith("characters/")
} | {"player"}


def _stem(ref: str) -> str:
    return ref.rsplit(".", 1)[0] if "." in ref else ref


def segments(beats):
    """The playable steps one scene collapses into."""
    segs, place, char = [], None, None
    for b in beats:
        if b.type == "background":
            if _stem(b.ref) in CHARACTERS:
                char = b.ref
            else:
                place, char = b.ref, None
        elif b.type == "dialogue":
            last = segs[-1] if segs else None
            if last and last["kind"] == "dialogue" and last["bg"] == place and last["ch"] == char:
                last["n"] += 1
            else:
                segs.append({"kind": "dialogue", "bg": place, "ch": char, "n": 1})
        elif b.type in ("system", "interactive", "mission", "choice"):
            segs.append({
                "kind": b.type, "bg": place, "ch": char, "ref": b.ref,
                "opts": [o["target"] for o in (b.options or [])],
            })
    return segs


def main() -> None:
    failures = []

    for sid, scene in SCENES.items():
        segs = segments(scene.beats)
        if not segs:
            failures.append(f"{sid}: no playable segments — shows the end screen immediately")

        for seg in segs:
            if seg["kind"] == "mission" and seg["ref"] not in CHALLENGES:
                failures.append(f"{sid}: mission '{seg['ref']}' has no challenge file")
            if seg["kind"] == "interactive" and seg["ref"] not in INTERACTIONS:
                failures.append(f"{sid}: interactive '{seg['ref']}' has no interaction file")
            if seg["kind"] == "choice":
                for target in seg["opts"]:
                    if target not in SCENES:
                        failures.append(f"{sid}: choice jumps to missing scene '{target}'")
            # A cutout with nothing behind it is a figure floating in black.
            if seg["ch"] and not seg["bg"]:
                failures.append(f"{sid}: character '{seg['ch']}' has no location behind it")

        if scene.next_scene and scene.next_scene not in SCENES:
            failures.append(f"{sid}: next: '{scene.next_scene}' does not exist")
        for cond in scene.conditions:
            if cond.next_scene not in SCENES:
                failures.append(f"{sid}: condition -> '{cond.next_scene}' does not exist")

    # The step-through widgets index into their own `code` array, so an
    # out-of-range line renders a blank or crashes the beat.
    for iid, item in INTERACTIONS.items():
        cfg = item.config
        if item.widget == "trace_loop":
            code, steps = cfg.get("code") or [], cfg.get("steps") or []
            if not code or not steps:
                failures.append(f"{iid}: trace_loop needs both code and steps")
            for n, step in enumerate(steps):
                for key in ("line", "variable", "value"):
                    if key not in step:
                        failures.append(f"{iid}: step {n} missing '{key}'")
                line = step.get("line")
                if isinstance(line, int) and not 0 <= line < len(code):
                    failures.append(f"{iid}: step {n} line {line} outside the snippet")
        elif item.widget == "fix_the_bug":
            code, fixes = cfg.get("code") or [], cfg.get("fixes") or []
            bug = cfg.get("bug_line")
            if not code or not fixes:
                failures.append(f"{iid}: fix_the_bug needs both code and fixes")
            if not isinstance(bug, int) or not 0 <= bug < len(code):
                failures.append(f"{iid}: bug_line {bug} outside the snippet")
            elif not code[bug].strip():
                failures.append(f"{iid}: bug_line points at a blank line")
            if sum(1 for f in fixes if f.get("correct")) != 1:
                failures.append(f"{iid}: needs exactly one correct fix")
            for key in cfg.get("line_hints") or {}:
                if not 0 <= int(key) < len(code):
                    failures.append(f"{iid}: line_hint {key} outside the snippet")
                elif int(key) == bug:
                    failures.append(f"{iid}: line_hint sits on the bug line")

    # The main spine must run start to finish without looping or dead-ending.
    seen, current = [], "awakening"
    while current and current not in seen:
        seen.append(current)
        scene = SCENES.get(current)
        if not scene:
            failures.append(f"spine: '{current}' does not exist")
            break
        choices = [s for s in segments(scene.beats) if s["kind"] == "choice"]
        current = choices[0]["opts"][0] if choices else scene.next_scene

    if current in seen:
        failures.append(f"spine loops back to '{current}'")

    # Authored but unreachable content is a wiring mistake, not a spare.
    referenced = {
        b.ref for scene in SCENES.values() for b in scene.beats
        if b.type in ("mission", "interactive")
    }
    for orphan in sorted(set(CHALLENGES) - referenced):
        failures.append(f"orphan challenge never played: {orphan}")
    for orphan in sorted(set(INTERACTIONS) - referenced):
        failures.append(f"orphan interaction never played: {orphan}")

    print(f"spine: {len(seen)} scenes, ends at {current!r}")
    for f in failures:
        print("FAIL:", f)
    assert not failures, f"{len(failures)} content failures"
    assert len(seen) >= 17, f"spine collapsed to {len(seen)} scenes"
    print("content OK")


if __name__ == "__main__":
    main()
