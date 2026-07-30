# Achievements — Catalogue and Design Philosophy

Achievements are already first-class: `reward.achievement` grants a named badge,
tracked on the player (`FIRST PROGRAM`, `DRAGON CONQUEROR`, `WISDOM OF THE
SYSTEM`, `DRAGON'S BLESSING/RECOGNITION`). This file proposes a full catalogue and
the rules for what earns one.

## Three kinds of achievement, three purposes

1. **Milestone** — "you learned a thing." One per concept cluster. These are the
   spine of a learner's sense of progress; they should feel *inevitable* if you
   play, and read like a transcript of skills. (These map 1:1 to B-chapters.)
2. **Mastery** — "you did it *well*, not just at all." Earned by the *shape* of a
   solution (a comprehension where a loop would pass, clean names, no crashes).
   These reward the professor's real goals and are *missable* — that's the point.
3. **Discovery / playful** — "you did something human." Failing charmingly,
   finding a secret, over-engineering, rage-guessing. These give the world a
   sense of humor and forgive mistakes by *celebrating* them.

Rule: **milestones are guaranteed, mastery and discovery are earned.** A learner
should never feel they *missed* learning; they should feel they can go deeper.

## Milestone achievements (one per cluster)

| Achievement | Earned by | Concept |
|---|---|---|
| `FIRST PROGRAM` ✅ | initializing your character | variables |
| `WISDOM OF THE SYSTEM` ✅ | finishing chapter 1b | vars·types·I/O |
| `THE DECIDER` | first working `if/elif/else` | conditionals |
| `MASTER OF SCALES` | finishing 2b | operators |
| `THE UNBOUND` | freeing the Warden (first correct loop exit) | loops |
| `KEEPER OF SLOTS` | first list indexed correctly | lists |
| `TRUE NAME` | first dict lookup by key | dicts |
| `SILVER TONGUE` | first `f`-string | strings |
| `SPELLWRIGHT` | first function that `return`s | functions |
| `WARD-BEARER` | first `try/except` that catches | exceptions |
| `THE SCRIBE'S HAND` | first file written | file I/O |
| `ONE BREATH` | first comprehension | comprehensions |
| `CREATOR` | first class instantiated | OOP |

## Mastery achievements (missable, reward *good* code)

| Achievement | Earned by | Teaches |
|---|---|---|
| `DRAGON CONQUEROR` ✅ | passing the DSA trial | you can do hard things |
| `DRAGON'S RECOGNITION` ✅ | balanced starting stats | restraint |
| `ELEGANT` | solve a loop chapter with a comprehension instead | DEX / Pythonic style |
| `CLEAN HANDS` | clear a boss with zero crashes and full MP | deliberation |
| `THE NAMER` | a mission where every variable name earns WIS | readability |
| `RIGHT TOOL` | use a dict where parallel lists would pass | data-structure choice |
| `NO REPEATS` | solve a set-based puzzle using an actual `set` | the set insight |
| `ONE-LINER` | collapse a 5+ line solution to one clean line | comprehensions mastery |
| `REFACTORER` | resubmit a passing solution as a *better* one (opt-in) | rewriting for quality |
| `POLYGLOT OF SELF` | define a class that uses another class | composition |

## Discovery / playful achievements

| Achievement | Earned by | Tone |
|---|---|---|
| `HELLO, VOID` | your first `print()` output | warm milestone-adjacent |
| `INFINITE WISDOM` | write your first infinite loop (and get rescued) | forgiving — failure celebrated |
| `IT'S A STRING` | try to do math on `input()` without `int()` | the classic beginner trap, named kindly |
| `OFF BY ONE` | index a list out of range once | the Quartermaster laughs, not scolds |
| `OVER-ENGINEER` | solve a tutorial challenge with 20+ lines | affectionate ribbing |
| `SPEEDRUN OF THE SOUL` | clear a chapter under N minutes | for the confident |
| `THE LONG ROAD` | use every hint on one challenge | *no shame* — hints are for using |
| `EASTER EGG: import this` | type `import this` in any editor | rewards curiosity |
| `NULL AND VOID` | encounter (and survive) the Null | lore discovery |
| `CARTOGRAPHER` | visit every location in an act | exploration |

## Titles vs achievements

The engine grants **titles** (`Awakened One`, `Dragon Conqueror`) separately from
achievements. Use the distinction:

- **Titles** = your *current* identity, shown in the HUD; you equip the one you
  like. They're expressive/cosmetic.
- **Achievements** = your *permanent record*, a checklist you can review.

Proposed titles to unlock (equippable, cosmetic): `The Decider`, `Loopbreaker`,
`Satchel-Keeper`, `Spellwright`, `Warder`, `The Nameless No More`, `Architect`.

## Design guardrails

- **Never gate story on a mastery/discovery achievement.** Milestones can be
  implicit gates (you finished the chapter); the missable ones are pure bonus.
- **Name them in-world.** `KEEPER OF SLOTS` beats `LISTS_101_COMPLETE`. The badge
  should sound like the game, not the syllabus.
- **Announce with the existing `system` panels.** `skill_learned` /`level_up`
  /`item_obtained` already exist ([docs/11_system_panels.md](../docs/11_system_panels.md));
  achievements should surface through them, not a new UI.
- **Track completion %** per act so a learner can *see* their transcript filling
  in — the single most motivating number for a from-scratch student.
