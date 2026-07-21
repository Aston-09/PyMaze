"""
Content Templating

Substitutes `{{token}}` placeholders in authored content with the live player's
values, so a chapter can talk about the character the learner actually built
instead of a hardcoded example.

Authors write:

    "You wrote: player_name = '{{player_name}}'"
    "hp = {{hp}}"

and the engine renders it against the current PlayerState at request time
(not load time — the player's stats change as they play).

Unknown tokens are left untouched rather than blanked, so a typo in a .scene
file shows up as a visible `{{oops}}` instead of silently vanishing.
"""
import re
from typing import Any, Dict, List

from app.models.player import PlayerState

_TOKEN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")

# Story-facing token -> PlayerState attribute. The aliases exist because the
# narrative refers to the learner's own Python variable names (`player_name`),
# which don't all match the internal field names (`name`).
_ALIASES = {
    "player_name": "name",
    "class": "class_name",
}

# Attributes a story file may read. Everything else on PlayerState (story_flags,
# completed_missions, ...) stays out of reach of authored text.
_EXPOSED = {
    "name", "class_name", "hp", "strength", "defense", "dexterity",
    "mana", "stamina", "xp", "gold", "level", "intelligence", "wisdom",
}


def build_context(player: PlayerState) -> Dict[str, Any]:
    """Flatten the player into the token namespace visible to authored content."""
    ctx = {field: getattr(player, field) for field in _EXPOSED}
    for alias, field in _ALIASES.items():
        ctx[alias] = getattr(player, field)
    return ctx


def render(value: Any, ctx: Dict[str, Any]) -> Any:
    """Recursively substitute tokens through strings, lists and dicts.

    Non-string leaves (ints, bools, None) pass through untouched, so challenge
    JSON keeps its types.
    """
    if isinstance(value, str):
        return _TOKEN.sub(
            lambda m: str(ctx[m.group(1)]) if m.group(1) in ctx else m.group(0),
            value,
        )
    if isinstance(value, list):
        return [render(v, ctx) for v in value]
    if isinstance(value, dict):
        return {k: render(v, ctx) for k, v in value.items()}
    return value


def render_for(value: Any, player: PlayerState) -> Any:
    """Convenience wrapper: build the context and render in one call."""
    return render(value, build_context(player))


def demo() -> None:
    """Self-check: the behaviours the story and challenge files depend on."""
    p = PlayerState(name="Aston", hp=250, strength=30, mana=80)

    # Aliased and direct tokens both resolve.
    assert render_for("I am {{player_name}}.", p) == "I am Aston."
    assert render_for("hp = {{hp}}", p) == "hp = 250"
    assert render_for("{{ strength }}", p) == "30"  # whitespace tolerated

    # The exact bug this module exists to fix: a challenge's expected output
    # must follow the player, not a hardcoded "Aston".
    hero = PlayerState(name="Lyra", hp=180)
    assert render_for("{{player_name}}\n{{hp}}\n", hero) == "Lyra\n180\n"

    # Nested structures keep their shape and non-string types.
    out = render_for(
        {"tests": [{"expected": "{{player_name}}", "xp": 20, "ok": True}]}, p
    )
    assert out == {"tests": [{"expected": "Aston", "xp": 20, "ok": True}]}

    # Unknown tokens survive visibly; private fields are not reachable.
    assert render_for("{{nope}}", p) == "{{nope}}"
    assert render_for("{{story_flags}}", p) == "{{story_flags}}"

    print("templating: all checks passed")


if __name__ == "__main__":
    demo()
