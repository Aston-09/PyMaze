"""
.scene DSL Parser

Reads .scene files from the story/ directory and returns ParsedScene objects.
The parser is line-based and tag-driven. It never contains story content itself.
"""
import os
import re
from typing import Dict, List, Optional
from app.models.scene import (
    ParsedScene, SceneDialogue, SceneReward, SceneCondition, SceneBeat,
)


def parse_scene_file(filepath: str) -> List[ParsedScene]:
    """Parse a single .scene file. Returns a list of ParsedScene objects
    (a file may contain multiple @scene blocks)."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    scenes = []
    # Split on @scene declarations
    raw_blocks = re.split(r"^@scene\s+", content, flags=re.MULTILINE)

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        scene_id = lines[0].strip()
        scene = _parse_block(scene_id, lines[1:])
        scenes.append(scene)

    return scenes


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


def load_all_scenes(story_dir: str) -> Dict[str, ParsedScene]:
    """Discover and load all .scene files from the story directory.
    Returns a dict keyed by scene_id."""
    scenes: Dict[str, ParsedScene] = {}

    if not os.path.isdir(story_dir):
        return scenes

    for filename in sorted(os.listdir(story_dir)):
        if filename.endswith(".scene"):
            filepath = os.path.join(story_dir, filename)
            for scene in parse_scene_file(filepath):
                scenes[scene.scene_id] = scene

    return scenes


def _selfcheck() -> None:
    """Assert the choice: beat parses. Run: python -m app.engine.story_loader"""
    import tempfile
    sample = (
        "@scene t\n"
        "dialogue:\n"
        '"The path forks."\n'
        "choice:\n"
        '"Go left." -> scene_left\n'
        '"Take the coward\'s road." -> scene_right\n'
        "dialogue:\n"
        '"(unreachable — choices jump away)"\n'
    )
    with tempfile.NamedTemporaryFile("w", suffix=".scene", delete=False, encoding="utf-8") as f:
        f.write(sample)
        path = f.name
    try:
        [scene] = parse_scene_file(path)
    finally:
        os.remove(path)

    choices = [b for b in scene.beats if b.type == "choice"]
    assert len(choices) == 1, f"expected 1 choice beat, got {len(choices)}"
    opts = choices[0].options
    assert opts == [
        {"label": "Go left.", "target": "scene_left"},
        {"label": "Take the coward's road.", "target": "scene_right"},
    ], opts
    print("story_loader: choice parsing ok")


if __name__ == "__main__":
    _selfcheck()
