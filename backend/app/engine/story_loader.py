"""
.scene / .txt DSL Parser

Reads story files from the story/ directory and returns ParsedScene objects,
plus any @challenge blocks authored inline (docs/12_txt_authoring.md).
The parser is line-based and tag-driven. It never contains story content itself.
"""
import os
import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from pydantic import ValidationError
from app.models.scene import (
    ParsedScene, SceneDialogue, SceneReward, SceneCondition, SceneBeat,
)
from app.models.challenge import ChallengeDefinition

log = logging.getLogger(__name__)

# .scene and .txt are parsed identically — the extension carries no meaning.
CONTENT_SUFFIXES = (".scene", ".txt")


def parse_scene_file(filepath: str) -> List[ParsedScene]:
    """Parse a single story file and return only its @scene blocks."""
    return parse_content_file(filepath)[0]


def parse_content_file(filepath: str) -> Tuple[List[ParsedScene], List[ChallengeDefinition]]:
    """Parse a single story file. Returns (scenes, inline challenges).

    A file may hold any number of @scene and @challenge blocks, in any order.
    A malformed @challenge is skipped with a logged error so one bad block
    cannot cost the file its scenes.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    scenes: List[ParsedScene] = []
    challenges: List[ChallengeDefinition] = []
    # Split on @scene / @challenge declarations, keeping the tag that matched.
    parts = re.split(r"^@(scene|challenge)\s+", content, flags=re.MULTILINE)

    for tag, block in zip(parts[1::2], parts[2::2]):
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        block_id = lines[0].strip()
        if tag == "scene":
            scenes.append(_parse_block(block_id, lines[1:]))
        else:
            try:
                challenges.append(_parse_challenge_block(block_id, lines[1:]))
            except (ValidationError, ValueError, TypeError, IndexError) as exc:
                log.error(
                    "Skipping invalid @challenge '%s' in %s: %s",
                    block_id, os.path.basename(filepath), exc,
                )

    return scenes, challenges


def _parse_block(scene_id: str, lines: List[str]) -> ParsedScene:
    """Parse the body of a single @scene block."""
    background = None
    music = None
    dialogues: List[SceneDialogue] = []
    beats: List[SceneBeat] = []
    mission = None
    reward_data: Dict = {}
    conditions: List[SceneCondition] = []
    next_scene = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # background: filename
        # The first one sets the scene's opening image; any later one is a
        # beat, so a chapter can change location mid-scene (the dragon's sky
        # dissolving into the Sage's hall) without splitting the file.
        if line.startswith("background:"):
            value = line.split(":", 1)[1].strip()
            if background is None:
                background = value
            beats.append(SceneBeat(type="background", ref=value))

        # music: filename
        elif line.startswith("music:"):
            music = line.split(":", 1)[1].strip()

        # system <variant>:   — a System UI panel, not narration.
        # First quoted line is the panel title, the rest is its body.
        elif line.startswith("system ") and line.rstrip().endswith(":"):
            variant = line[7:].rstrip(":").strip().lower()
            panel_lines = []
            i += 1
            while i < len(lines):
                pl = lines[i].strip()
                if pl.startswith('"') and pl.endswith('"'):
                    panel_lines.append(pl.strip('"'))
                    i += 1
                else:
                    break
            beats.append(SceneBeat(type="system", ref=variant, lines=panel_lines))
            continue

        # npc Name:
        elif line.startswith("npc "):
            speaker = line[4:].rstrip(":").strip()
            dialogue_lines = []
            i += 1
            while i < len(lines):
                dl = lines[i].strip()
                if dl.startswith('"') and dl.endswith('"'):
                    dialogue_lines.append(dl.strip('"'))
                    i += 1
                else:
                    break
            dialogues.append(SceneDialogue(speaker=speaker, lines=dialogue_lines))
            beats.append(SceneBeat(type="dialogue", speaker=speaker, lines=dialogue_lines))
            continue  # skip the i += 1 at the bottom

        # dialogue: (narrator)
        elif line.startswith("dialogue:"):
            dialogue_lines = []
            i += 1
            while i < len(lines):
                dl = lines[i].strip()
                if dl.startswith('"') and dl.endswith('"'):
                    dialogue_lines.append(dl.strip('"'))
                    i += 1
                else:
                    break
            dialogues.append(SceneDialogue(speaker="narrator", lines=dialogue_lines))
            beats.append(SceneBeat(type="dialogue", speaker="narrator", lines=dialogue_lines))
            continue

        # mission: challenge_id
        elif line.startswith("mission:"):
            val = line.split(":", 1)[1].strip()
            if not val:
                # challenge_id is on the next line
                i += 1
                val = lines[i].strip() if i < len(lines) else ""
            if val:
                beats.append(SceneBeat(type="mission", ref=val))
                # `mission` keeps the legacy single-mission contract: the first
                # one authored. Later missions live in `beats` only.
                if mission is None:
                    mission = val

        # interactive: interaction_id
        elif line.startswith("interactive:"):
            val = line.split(":", 1)[1].strip()
            if not val:
                i += 1
                val = lines[i].strip() if i < len(lines) else ""
            if val:
                beats.append(SceneBeat(type="interactive", ref=val))

        # choice:  — branching the player drives, not the engine.
        #   "Label the player reads" -> target_scene_id
        # Unlike condition:/next: (which routes on stats), a choice is a real
        # decision beat: the client shows the labels and jumps to whichever
        # target is picked. That's what gives a chapter multiple endings keyed
        # to what the player *chooses*, not what their stats happen to be.
        elif line.startswith("choice:"):
            options: List[Dict[str, str]] = []
            i += 1
            while i < len(lines):
                ol = lines[i].strip()
                m = re.match(r'^"(.*)"\s*->\s*(\S+)$', ol)
                if not m:
                    break
                options.append({"label": m.group(1), "target": m.group(2)})
                i += 1
            if options:
                beats.append(SceneBeat(type="choice", options=options))
            continue

        # reward: block
        elif line.startswith("reward:"):
            i += 1
            while i < len(lines):
                rl = lines[i].strip()
                if not rl:
                    break
                if ":" in rl:
                    key, val = rl.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    if key == "xp":
                        reward_data["xp"] = int(val)
                    elif key == "gold":
                        reward_data["gold"] = int(val)
                    elif key == "title":
                        reward_data["title"] = val
                    elif key == "achievement":
                        reward_data["achievement"] = val
                else:
                    break
                i += 1
            continue

        # achievement: name
        elif line.startswith("achievement:"):
            ach = line.split(":", 1)[1].strip()
            if not reward_data:
                reward_data = {}
            reward_data["achievement"] = ach

        # condition: expression -> next scene
        elif line.startswith("condition:"):
            expr = line.split(":", 1)[1].strip()
            # Look for next: on the following line
            i += 1
            if i < len(lines):
                nl = lines[i].strip()
                if nl.startswith("next:"):
                    target = nl.split(":", 1)[1].strip()
                    conditions.append(SceneCondition(expression=expr, next_scene=target))

        # next: scene_id
        elif line.startswith("next:"):
            val = line.split(":", 1)[1].strip()
            if val:
                next_scene = val
            else:
                i += 1
                if i < len(lines):
                    next_scene = lines[i].strip()

        i += 1

    reward = SceneReward(**reward_data) if reward_data else None

    return ParsedScene(
        scene_id=scene_id,
        background=background,
        music=music,
        beats=beats,
        dialogues=dialogues,
        mission=mission,
        reward=reward,
        conditions=conditions,
        next_scene=next_scene,
    )


# Section keywords that close a raw `code:` block. Anything at column 0 that
# reads like one of these ends the block; everything else is starter code.
_SECTION_RE = re.compile(
    r"^(?:topic|difficulty|title|tests|test|narrative|instructions|code|hints"
    r"|variables|reward|@scene|@challenge)(?::|\s|$)"
)


def _quoted(lines: List[str], i: int) -> Tuple[List[str], int]:
    """Collect consecutive "quoted" lines from i. The npc/dialogue inner loop
    (see _parse_block above), factored out. Returns the lines and the cursor."""
    out: List[str] = []
    while i < len(lines):
        ql = lines[i].strip()
        if ql.startswith('"') and ql.endswith('"'):
            out.append(ql.strip('"'))
            i += 1
        else:
            break
    return out, i


def _parse_challenge_block(challenge_id: str, lines: List[str]) -> ChallengeDefinition:
    """Parse the body of a single @challenge block into a ChallengeDefinition.

    Raises (ValidationError / ValueError) on a malformed block — the caller
    logs and skips it.
    """
    data: Dict = {"challenge_id": challenge_id}

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # topic: / difficulty: / title:  — scalars on one line
        if line.startswith(("topic:", "difficulty:", "title:")):
            key = line.split(":", 1)[0].strip()
            data[key] = line.split(":", 1)[1].strip()

        # test: <form>  — collapses test_type and its companion fields
        elif line.startswith("test:"):
            words = line.split(":", 1)[1].split()
            kind, args = (words[0] if words else ""), words[1:]
            if kind == "function":
                data["test_type"] = "function"
                if args:
                    data["function_name"] = args[0]
            elif kind == "variables":
                data["test_type"] = "variables"
                data["applies_stats"] = "stats" in args
            elif kind in ("script", "output"):
                data["test_type"] = "script_variable" if kind == "script" else "script_output"
                for arg in args:  # in= / out= are keyword tokens, order-free
                    if arg.startswith("in="):
                        data["input_variable"] = arg[3:]
                    elif arg.startswith("out="):
                        data["output_variable"] = arg[4:]
            else:
                log.warning("challenge '%s': unknown test form: %s", challenge_id, line)

        # narrative: / instructions: / hints:  — quoted lines, like dialogue:
        elif line.startswith("narrative:"):
            quoted, i = _quoted(lines, i + 1)
            data["narrative"] = "\n".join(quoted)
            continue

        elif line.startswith("instructions:"):
            quoted, i = _quoted(lines, i + 1)
            data["instructions"] = "\n".join(quoted)
            continue

        elif line.startswith("hints:"):
            data["hints"], i = _quoted(lines, i + 1)
            continue

        # code:  — the one raw block. Verbatim, indentation intact.
        # ponytail: keyword-terminated raw block. Breaks only if starter code has a
        # column-0 line literally named like a section tag. Switch to a fenced
        # delimiter if that ever happens.
        elif line.startswith("code:"):
            code_lines: List[str] = []
            i += 1
            while i < len(lines) and not _SECTION_RE.match(lines[i]):
                code_lines.append(lines[i])
                i += 1
            while code_lines and not code_lines[-1].strip():
                code_lines.pop()  # trailing blanks only — interior ones are code
            data["starting_code"] = "\n".join(code_lines)
            continue

        # tests:  — one `<json> -> <json>` per line
        elif line.startswith("tests:"):
            tests: List[Dict] = []
            i += 1
            while i < len(lines):
                tl = lines[i].strip()
                if not tl or _SECTION_RE.match(lines[i]):
                    break
                # First arrow whose two sides both parse as JSON wins, so an
                # arrow inside a string literal does not break the line.
                for arrow in re.finditer(r"->", tl):
                    try:
                        case = {
                            "input": json.loads(tl[:arrow.start()]),
                            "expected": json.loads(tl[arrow.end():]),
                        }
                    except ValueError:
                        continue
                    tests.append(case)
                    break
                else:
                    log.warning(
                        "challenge '%s': skipping unparsable test line: %s",
                        challenge_id, tl,
                    )
                i += 1
            data["validation_tests"] = tests
            continue

        # variables:  — name: type, the reward: key-value shape
        elif line.startswith("variables:"):
            expected: Dict[str, str] = {}
            i += 1
            while i < len(lines):
                vl = lines[i].strip()
                if not vl or ":" not in vl:
                    break
                name, vtype = vl.split(":", 1)
                expected[name.strip()] = vtype.strip()
                i += 1
            data["expected_variables"] = expected
            continue

        # reward: block — identical to the scene reward:
        elif line.startswith("reward:"):
            reward_data: Dict = {}
            i += 1
            while i < len(lines):
                rl = lines[i].strip()
                if not rl:
                    break
                if ":" in rl:
                    key, val = rl.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    if key == "xp":
                        reward_data["xp"] = int(val)
                    elif key == "gold":
                        reward_data["gold"] = int(val)
                    elif key == "title":
                        reward_data["title"] = val
                    elif key == "achievement":
                        reward_data["achievement"] = val
                else:
                    break
                i += 1
            if reward_data:
                data["reward"] = reward_data
            continue

        i += 1

    return ChallengeDefinition(**data)


def load_all_scenes(story_dir: str) -> Dict[str, ParsedScene]:
    """Discover and load all story files from the story directory.
    Returns a dict keyed by scene_id."""
    scenes: Dict[str, ParsedScene] = {}

    if not os.path.isdir(story_dir):
        return scenes

    for filename in sorted(os.listdir(story_dir)):
        if filename.endswith(CONTENT_SUFFIXES):
            filepath = os.path.join(story_dir, filename)
            for scene in parse_scene_file(filepath):
                scenes[scene.scene_id] = scene

    return scenes


def load_inline_challenges(story_dir: str) -> Dict[str, ChallengeDefinition]:
    """Load every @challenge authored inline in the story directory.
    Returns a dict keyed by challenge_id."""
    challenges: Dict[str, ChallengeDefinition] = {}

    if not os.path.isdir(story_dir):
        return challenges

    for filename in sorted(os.listdir(story_dir)):
        if not filename.endswith(CONTENT_SUFFIXES):
            continue
        for challenge in parse_content_file(os.path.join(story_dir, filename))[1]:
            if challenge.challenge_id in challenges:
                log.warning(
                    "Duplicate challenge_id '%s' in %s — overwriting the earlier one.",
                    challenge.challenge_id, filename,
                )
            challenges[challenge.challenge_id] = challenge

    return challenges


def _selfcheck() -> None:
    """Assert choice: and @challenge parsing. Run: python -m app.engine.story_loader"""
    import tempfile
    scene_src = (
        "@scene t\n"
        "dialogue:\n"
        '"The path forks."\n'
        "choice:\n"
        '"Go left." -> scene_left\n'
        '"Take the coward\'s road." -> scene_right\n'
        "dialogue:\n"
        '"(unreachable — choices jump away)"\n'
        "mission: m1\n"
    )
    # Same file: a @scene, two good @challenge blocks and one broken one.
    challenge_src = (
        "\n@challenge m1\n"
        "topic: Lists\n"
        "difficulty: easy\n"
        "title: The Ledger\n"
        "test: function f\n"
        "narrative:\n"
        '"N."\n'
        "instructions:\n"
        '"I."\n'
        "code:\n"
        "def f(coins):\n"
        "    # Your solution here\n"
        "\n"
        "    return coins\n"
        "\n"
        "tests:\n"
        "[[3, 1, 2]] -> [1, 2, 3]\n"
        "oops -> nope\n"  # not JSON either side — warn and skip, never crash
        "hints:\n"
        '"Lists have .sort()."\n'
        "reward:\n"
        "xp: 100\n"
        "\n@challenge m2\n"
        "topic: Loops\n"
        "difficulty: easy\n"
        "title: The Tally\n"
        "test: script in=nums out=total\n"
        "narrative:\n"
        '"N2."\n'
        "instructions:\n"
        '"I2."\n'
        "code:\n"
        "total = 0\n"
        "\n@challenge broken\n"  # no title: — must be skipped, not raised
        "topic: Lists\n"
        "difficulty: easy\n"
        "narrative:\n"
        '"NB."\n'
        "instructions:\n"
        '"IB."\n'
        "code:\n"
        "x = 1\n"
        # the remaining three test: forms — variables, variables stats, output
        "\n@challenge m3\n"
        "topic: Variables\n"
        "difficulty: tutorial\n"
        "title: The Name\n"
        "test: variables\n"
        "narrative:\n"
        '"N3."\n'
        "instructions:\n"
        '"I3."\n'
        "code:\n"
        'player_name = ""\n'
        "\n"
        "variables:\n"
        "player_name: str\n"
        "hp: int\n"
        "\n@challenge m4\n"
        "topic: Variables\n"
        "difficulty: tutorial\n"
        "title: The Judgment\n"
        "test: variables stats\n"
        "narrative:\n"
        '"N4."\n'
        "instructions:\n"
        '"I4."\n'
        "code:\n"
        "strength = 0\n"
        "\n@challenge m5\n"
        "topic: Output\n"
        "difficulty: easy\n"
        "title: The Herald\n"
        "test: output in=name\n"
        "narrative:\n"
        '"N5."\n'
        "instructions:\n"
        '"I5."\n'
        "code:\n"
        "print(name)\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(scene_src + challenge_src)
        path = f.name
    try:
        scenes, challenges = parse_content_file(path)
        compat = parse_scene_file(path)  # the shim still returns a list of scenes
    finally:
        os.remove(path)

    # --- the @scene half is untouched by the @challenge blocks beside it ---
    [scene] = scenes
    assert [s.scene_id for s in compat] == ["t"], compat
    choices = [b for b in scene.beats if b.type == "choice"]
    assert len(choices) == 1, f"expected 1 choice beat, got {len(choices)}"
    opts = choices[0].options
    assert opts == [
        {"label": "Go left.", "target": "scene_left"},
        {"label": "Take the coward's road.", "target": "scene_right"},
    ], opts
    assert scene.mission == "m1", scene.mission

    # --- the @challenge half ---
    by_id = {c.challenge_id: c for c in challenges}
    assert set(by_id) == {"m1", "m2", "m3", "m4", "m5"}, set(by_id)  # 'broken' skipped, not fatal
    m1, m2, m3, m4, m5 = (by_id[k] for k in ("m1", "m2", "m3", "m4", "m5"))

    assert (m1.test_type, m1.function_name) == ("function", "f"), m1.test_type
    assert m1.validation_tests == [{"input": [[3, 1, 2]], "expected": [1, 2, 3]}], m1.validation_tests
    assert isinstance(m1.validation_tests[0]["input"][0], list), "JSON types must survive"
    assert m1.starting_code == (
        "def f(coins):\n    # Your solution here\n\n    return coins"
    ), repr(m1.starting_code)
    assert m1.narrative == "N." and m1.instructions == "I.", m1.narrative
    assert m1.hints == ["Lists have .sort()."], m1.hints
    assert m1.reward.xp == 100, m1.reward

    assert (m2.test_type, m2.input_variable, m2.output_variable) == (
        "script_variable", "nums", "total",
    ), m2.test_type

    # `test: variables` reads the variables: block and leaves stats alone.
    assert (m3.test_type, m3.applies_stats) == ("variables", False), m3.test_type
    assert m3.expected_variables == {"player_name": "str", "hp": "int"}, m3.expected_variables
    assert m3.starting_code == 'player_name = ""', repr(m3.starting_code)

    # `test: variables stats` is the same type with character creation on.
    assert (m4.test_type, m4.applies_stats) == ("variables", True), m4.applies_stats

    # `test: output in=` compares stdout — an input variable, no output one.
    assert (m5.test_type, m5.input_variable, m5.output_variable) == (
        "script_output", "name", None,
    ), m5.test_type

    print("story_loader: choice + @challenge parsing ok")


if __name__ == "__main__":
    _selfcheck()
