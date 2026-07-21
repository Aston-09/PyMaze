"""
Save System

Persists and loads PlayerState as JSON files in the saves/ directory.
"""
import os
import json
from app.models.player import PlayerState


SAVES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "saves")


def save_game(player: PlayerState, slot: str = "autosave") -> str:
    """Save the player state to a JSON file. Returns the filepath."""
    os.makedirs(SAVES_DIR, exist_ok=True)
    filepath = os.path.join(SAVES_DIR, f"{slot}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(player.model_dump(), f, indent=2)

    return filepath


def load_game(slot: str = "autosave") -> PlayerState | None:
    """Load player state from a save file. Returns None if not found."""
    filepath = os.path.join(SAVES_DIR, f"{slot}.json")

    if not os.path.exists(filepath):
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return PlayerState(**data)


def list_saves() -> list[str]:
    """List all available save slots."""
    if not os.path.isdir(SAVES_DIR):
        return []
    return [f.replace(".json", "") for f in os.listdir(SAVES_DIR) if f.endswith(".json")]
