# Engine Architecture

## Objective
Build PyBe as a modular game engine, rather than a hardcoded game. The engine must read story files, load referenced assets, execute coding challenges, update player state, and move to the next scene automatically.

## Recommended Folder Structure
```text
PyBe/
engine/
    story_loader.py
    asset_loader.py
    battle_engine.py
    scoring.py
    challenge_checker.py
    player.py
    save_system.py
    ui.py

story/
    chapter_0.scene
    chapter_1.scene

assets/
    backgrounds/
    characters/
    music/
    sound/
    animations/

challenges/
    variables.json
    loops.json

saves/
config/
main.py
```

## Core Modules
- **Story Loader**: Automatically discovers and parses `.scene` files using our custom DSL.
- **Asset Loader**: Fetches images, sounds, and music referenced dynamically in `.scene` files.
- **Challenge Checker (Executor)**: Safely runs user-submitted Python code in an isolated environment against deterministic validation tests.
- **Scoring Engine**: Evaluates code quality, syntax, and output to award XP, Gold, INT, WIS, and DEX.

## Save System
Saves must persist the player's journey. Required data to save:
- Current chapter and step
- Player stats (HP, INT, WIS, DEX, etc.)
- Inventory and Gold
- Earned XP and Achievements
- Completed missions and Story flags
- Choices made

Loads should happen automatically when the player chooses to continue.

## Event System
The engine must be heavily **Event-driven**. For example, completing a challenge fires a `MISSION_COMPLETE` event, which the UI listens to for rendering the "Success" modal, the `player.py` listens to for awarding XP, and the `story_loader.py` listens to for advancing to the next scene tag.
