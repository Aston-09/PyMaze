# RPG System

PyMaze integrates traditional RPG progression mechanics tied directly to coding proficiency and story progression.

## Base Stats
The player's character consists of canonical combat stats and programmer statistics. 
- **HP (Health Points)**: Base 100. Used during battles.
- **Strength**: Base 10. Physical attacks.
- **Defense**: Base 10. Damage reduction.
- **Dexterity**: Base 10. Dodge chance / initiative.
- **Mana**: Base 50. Spell casting.
- **Stamina**: Base 100. Physical skills.
- **XP**: Base 0. Level progression.
- **Gold**: Base 100. Buy equipment.

## Alignment & Balancing Rules (The Dragon's Judgment)
During the initial initialization phase (where users write variables to define their stats), the engine enforces balancing through narrative events:
- **Rule 1 (Weak Character):** If stats are set below the minimums, the Dragon grants the "Blessing of the Dragon," raising stats to the canonical base values automatically.
- **Rule 2 (Balanced Character):** If stats are within the acceptable range, the player keeps them exactly as written and earns the "Dragon's Recognition" achievement.
- **Rule 3 (Overpowered Character):** If stats exceed maximum allowed values, the Dragon becomes enraged and initiates a high-level DSA "Trial of the Dragon." If the player passes, they keep the overpowered stats. If they fail, they are reset to the base values.

## Other Mechanics
- **Battles**: Turn-based combat where spells and attacks are executed by writing small snippets of code within time limits.
- **Inventory & Shop**: Gold earned from quests can be used to buy cosmetic character skins, pets, and visual spell animations. (Not for buying progress).
- **Reputation (🌟)**: High reputation unlocks secret merchants and side quests.
