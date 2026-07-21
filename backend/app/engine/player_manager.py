"""
Player Manager

Manages the in-memory player state. Contains the Dragon's Judgment logic
and handles stat updates from challenge completions.
"""
from typing import Dict, Any, Tuple
from app.models.player import PlayerState, BASE_STATS, MAX_STATS


# In-memory player state (single-player prototype)
_player: PlayerState = PlayerState()


def get_player() -> PlayerState:
    """Return the current player state."""
    return _player


def reset_player() -> PlayerState:
    """Reset player to default state."""
    global _player
    _player = PlayerState()
    return _player


def update_player_from_variables(user_vars: Dict[str, Any]) -> PlayerState:
    """After Chapter 0's 'variables' challenge, apply the user-defined
    stats to the player object."""
    global _player

    if "player_name" in user_vars and isinstance(user_vars["player_name"], str):
        _player.name = user_vars["player_name"]
    if "class_name" in user_vars and isinstance(user_vars["class_name"], str):
        _player.class_name = user_vars["class_name"]

    # Map user variables to player stats
    stat_mapping = {
        "hp": "hp",
        "strength": "strength",
        "defense": "defense",
        "dexterity": "dexterity",
        "mana": "mana",
        "stamina": "stamina",
    }

    for var_name, attr_name in stat_mapping.items():
        if var_name in user_vars and isinstance(user_vars[var_name], (int, float)):
            setattr(_player, attr_name, int(user_vars[var_name]))

    return _player


def judge_stats() -> Tuple[str, str]:
    """The Dragon's Judgment.

    Returns:
        (judgment, narrative):
        - judgment: "weak", "balanced", or "overpowered"
        - narrative: the dragon's dialogue
    """
    is_weak = False
    is_overpowered = False

    for stat_name, min_val in BASE_STATS.items():
        if stat_name in ("xp", "gold"):
            continue
        current = getattr(_player, stat_name, min_val)
        if current < min_val:
            is_weak = True

    for stat_name, max_val in MAX_STATS.items():
        current = getattr(_player, stat_name, 0)
        if current > max_val:
            is_overpowered = True

    if is_overpowered:
        return "overpowered", (
            "The dragon's eyes ignite.\n"
            "\"You...\"\n"
            "\"You would steal power you have not earned.\"\n"
            "\"Then prove yourself.\"\n"
            "\"Face the Trial of the Dragon.\""
        )
    elif is_weak:
        return "weak", (
            "The dragon smiles.\n"
            "\"You possess neither strength nor experience.\"\n"
            "\"But every legend begins as a weakling.\"\n"
            "\"I grant you the Blessing of the Dragon.\"\n"
            "\"Survive until we meet again.\""
        )
    else:
        return "balanced", (
            "The dragon nods slowly.\n"
            "\"You have chosen wisely.\"\n"
            "\"Power earned through restraint endures.\"\n"
            "\"Walk your path.\"\n"
            "\"I shall watch.\""
        )


def apply_blessing() -> PlayerState:
    """Rule 1: Raise all stats below minimums to the base values."""
    global _player
    for stat_name, min_val in BASE_STATS.items():
        if stat_name in ("xp", "gold"):
            continue
        if getattr(_player, stat_name) < min_val:
            setattr(_player, stat_name, min_val)

    if "DRAGON'S BLESSING" not in _player.achievements:
        _player.achievements.append("DRAGON'S BLESSING")
    return _player


def apply_recognition() -> PlayerState:
    """Rule 2: Stats are fine. Just grant the achievement."""
    global _player
    if "DRAGON'S RECOGNITION" not in _player.achievements:
        _player.achievements.append("DRAGON'S RECOGNITION")
    return _player


def apply_reset() -> PlayerState:
    """Rule 3 (failed trial): Reset all stats to base values."""
    global _player
    for stat_name, base_val in BASE_STATS.items():
        setattr(_player, stat_name, base_val)

    return _player


def award_xp(amount: int) -> PlayerState:
    """Award XP and check for level-up."""
    global _player
    _player.xp += amount
    # Simple leveling: every 100 XP = 1 level
    _player.level = 1 + _player.xp // 100
    return _player


def award_gold(amount: int) -> PlayerState:
    global _player
    _player.gold += amount
    return _player


def award_stats(int_bonus: int = 0, wis_bonus: int = 0, dex_bonus: int = 0) -> PlayerState:
    global _player
    _player.intelligence += int_bonus
    _player.wisdom += wis_bonus
    # Note: dexterity is a combat stat; DEX bonus from coding maps to it
    _player.dexterity += dex_bonus
    return _player


def complete_mission(mission_id: str) -> PlayerState:
    global _player
    if mission_id not in _player.completed_missions:
        _player.completed_missions.append(mission_id)
    return _player


def unlock_achievement(name: str) -> PlayerState:
    global _player
    if name not in _player.achievements:
        _player.achievements.append(name)
    return _player


def advance_scene(scene_id: str) -> PlayerState:
    global _player
    _player.current_scene = scene_id
    return _player
