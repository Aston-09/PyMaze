"""
Player Manager

Stateless utility functions to mutate PlayerState.
"""
from typing import Dict, Any, Tuple
from datetime import date
from app.models.player import PlayerState, BASE_STATS, MAX_STATS

def update_player_from_variables(player: PlayerState, user_vars: Dict[str, Any]) -> PlayerState:
    """After Chapter 0's 'variables' challenge, apply the user-defined
    stats to the player object."""
    if "player_name" in user_vars and isinstance(user_vars["player_name"], str):
        player.name = user_vars["player_name"]
    if "class_name" in user_vars and isinstance(user_vars["class_name"], str):
        player.class_name = user_vars["class_name"]

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
            setattr(player, attr_name, int(user_vars[var_name]))

    return player

def judge_stats(player: PlayerState) -> Tuple[str, str]:
    is_weak = False
    is_overpowered = False

    for stat_name, min_val in BASE_STATS.items():
        if stat_name in ("xp", "gold"):
            continue
        current = getattr(player, stat_name, min_val)
        if current < min_val:
            is_weak = True

    for stat_name, max_val in MAX_STATS.items():
        current = getattr(player, stat_name, 0)
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

def apply_blessing(player: PlayerState) -> PlayerState:
    for stat_name, min_val in BASE_STATS.items():
        if stat_name in ("xp", "gold"):
            continue
        if getattr(player, stat_name) < min_val:
            setattr(player, stat_name, min_val)

    if "DRAGON'S BLESSING" not in player.achievements:
        player.achievements.append("DRAGON'S BLESSING")
    return player

def apply_recognition(player: PlayerState) -> PlayerState:
    if "DRAGON'S RECOGNITION" not in player.achievements:
        player.achievements.append("DRAGON'S RECOGNITION")
    return player

def apply_reset(player: PlayerState) -> PlayerState:
    for stat_name, base_val in BASE_STATS.items():
        setattr(player, stat_name, base_val)
    return player

def award_xp(player: PlayerState, amount: int) -> PlayerState:
    player.xp += amount
    player.level = 1 + player.xp // 100
    return player

def award_gold(player: PlayerState, amount: int) -> PlayerState:
    player.gold += amount
    return player

def award_stats(player: PlayerState, int_bonus: int = 0, wis_bonus: int = 0, dex_bonus: int = 0) -> PlayerState:
    player.intelligence += int_bonus
    player.wisdom += wis_bonus
    player.dexterity += dex_bonus
    return player

def complete_mission(player: PlayerState, mission_id: str) -> PlayerState:
    today_str = date.today().isoformat()
    if not player.activity_log:
        player.activity_log = {}
    player.activity_log[today_str] = player.activity_log.get(today_str, 0) + 1

    if mission_id not in player.completed_missions:
        player.completed_missions.append(mission_id)
    return player

def unlock_achievement(player: PlayerState, name: str) -> PlayerState:
    if name not in player.achievements:
        player.achievements.append(name)
    return player

def advance_scene(player: PlayerState, scene_id: str) -> PlayerState:
    player.current_scene = scene_id
    return player


def demo() -> None:
    """Self-check: the mutations every route depends on."""
    p = PlayerState()

    advance_scene(p, "chapter_2_trial_of_choice")
    assert p.current_scene == "chapter_2_trial_of_choice"

    award_xp(p, 250)
    assert p.xp == 250 and p.level == 3

    complete_mission(p, "variables_intro")
    complete_mission(p, "variables_intro")
    assert p.completed_missions == ["variables_intro"]

    # Overspending on stats is what summons the Trial; a default sheet is not.
    assert judge_stats(PlayerState())[0] == "balanced"
    over = PlayerState(**{k: v * 100 for k, v in MAX_STATS.items()})
    assert judge_stats(over)[0] == "overpowered"

    print("player_manager: all checks passed")


if __name__ == "__main__":
    demo()
