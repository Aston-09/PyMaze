"""Pydantic model for the player's persistent state."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


# Canonical base stats — the "world minimum" from the RPG system spec
BASE_STATS = {
    "hp": 100,
    "strength": 10,
    "defense": 10,
    "dexterity": 10,
    "mana": 50,
    "stamina": 100,
    "xp": 0,
    "gold": 100,
}

# Maximum allowed before "overpowered" triggers
MAX_STATS = {
    "hp": 500,
    "strength": 50,
    "defense": 50,
    "dexterity": 50,
    "mana": 200,
    "stamina": 500,
}


class PlayerState(BaseModel):
    """The complete, serializable state of a player."""
    name: str = "Unknown Traveler"
    class_name: str = "Wanderer"

    # Which of the two player sprite sets (assets/characters/player/<gender>/)
    # to show wherever a scene reflects the player's own art. None until the
    # one-time appearance picker runs; defaults to "male" at render time so
    # an old save or a skipped picker never points at a missing folder.
    gender: Optional[str] = None

    # Combat stats
    hp: int = BASE_STATS["hp"]
    strength: int = BASE_STATS["strength"]
    defense: int = BASE_STATS["defense"]
    dexterity: int = BASE_STATS["dexterity"]
    mana: int = BASE_STATS["mana"]
    stamina: int = BASE_STATS["stamina"]

    # Progression
    xp: int = 0
    gold: int = BASE_STATS["gold"]
    level: int = 1

    # Programmer stats (earned from code quality)
    intelligence: int = 0
    wisdom: int = 0

    # Journey tracking
    current_scene: str = "awakening"
    completed_missions: List[str] = []
    achievements: List[str] = []
    inventory: List[str] = []
    story_flags: Dict[str, Any] = {}
    activity_log: Dict[str, int] = {}
