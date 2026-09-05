# Curriculum Map — Python from Scratch, Braided into Story

The backbone. Every Python concept a beginner needs, ordered so each one has the
prerequisites it depends on, and each mapped to an **A** (story/apply) or **B**
(teach) chapter. This is the spine [02_story_arc.md](02_story_arc.md) hangs
narrative on and [03_characters.md](03_characters.md) hangs mentors on.

## Reading the table

- **B** rows are teaching chapters (Sage's-Library style, high interaction density).
- **A** rows are story chapters (one mission, real stakes, the concept *applied*).
- **A `B` always plays before its `A`.** The table is in play order: a concept is
  taught in the safe room first, then applied under stakes. Nothing may be asked
  of a learner that the braid has not already put in their hands — which also
  means no mission before 7b may require `def`.
- "Status" marks what already exists in `story/` and `challenges/`.

| # | Chapter (working title) | Type | Concept cluster | Metaphor | Status |
|---|---|---|---|---|---|
| 0 | The Awakening | A | Variables, data types (first contact) | chest | ✅ built |
| 1 | The Dragon's Trial | A | DSA boss (sliding window) — optional | procession of souls | ✅ built |
| 1b | Wisdom of the System | **B** | Variables · assignment · str/int/float/bool · `print()` · `input()` | chest · four families · mirror · crystal | ✅ built |
| 2 | Trial of Choice | A | `if` / `elif` / `else` | Gate of Choices | ✅ built |
| 2b | The Alchemist's Scales | **B** | Operators: arithmetic, comparison, logical, `and/or/not`, precedence | scales & reagents | ✅ built |
| 3b | The Echoing Halls | **B** | `while` vs `for`, `range`, accumulation, `break`/`continue`, the infinite-loop curse | cursed corridor | ✅ built |
| 3 | The Endless Bridge | A | Loops applied — cross a bridge that rebuilds each step | Echoing Halls | ✅ built |
| 4b | The Satchel of Many Slots | **B** | Lists: index from 0, slice, append/pop, `len`, iterate, negative index | satchel with numbered pockets | ✅ built |
| 4 | The Quartermaster's Caravan | A | Lists applied — pack a caravan, indexing, ordering | numbered satchel | ✅ built |
| 5b | The Card Catalogue | **B** | Dicts (key→value), `.get`, keys/values/items, nesting; tuples (sealed scrolls); sets (the unrepeating roster — callback to the Dragon Trial) | card catalogue · sealed scroll · guild roster | ✅ built |
| 5 | The Locked Grimoire | A | Dicts applied — a spellbook keyed by spell-name | grimoire | ✅ built |
| 6b | The Loom of Words | **B** | String indexing/slicing, `f`-strings, `.split/.join/.strip/.upper`, immutability | weaving | ✅ built |
| 6 | The Riddle Weaver | A | Strings applied — decode a riddle carved in runes | ribbon of runes | ✅ built |
| 7b | The Spellbook | **B** | `def`, parameters, `return`, arguments vs params, default args, docstrings | binding an incantation | ✅ built |
| 7c | The Private Workshop | **B** (short) | Scope: local vs global, why the workshop's whispers don't leave the room | workshop vs town square | ✅ built |
| 7 | The Enchanter's Bargain | A | Functions applied — inscribe a reusable battle-spell + recursion, branching endings | spellbook | ✅ built |
| 8 | The Corruption at the Well | A | Exceptions applied — a glitched zone that crashes the unwary | the Blight | 🔜 |
| 8b | The Warder's Circle | **B** | `try/except/else/finally`, exception types, raising, why crashes ≠ dead ends | protective wards | 🔜 |
| 9 | The Eternal Archive | A | File I/O applied — read the world's true record, write your name into it | ancient scrolls | 🔜 |
| 9b | The Scribe's Desk | **B** | `open`, read/write, `with`, lines, (JSON as a stretch) | scroll & quill | 🔜 |
| 10 | The One-Breath Duel | A | Comprehensions applied — a speed duel scored on DEX | the master's flourish | 🔜 |
| 10b | The Single Incantation | **B** (short) | List/dict/set comprehensions, when to use vs a loop | collapsing a loop to one line | 🔜 |
| 11 | The Loom of Creation | A | OOP applied — the player defines a *new kind of being* to fight beside them | the Loom | 🔜 |
| 11b | Blueprints of the Real | **B** | `class`, `__init__`, attributes, methods, `self`, instances; a taste of inheritance | blueprint → creature | 🔜 |
| 12 | Boss: The Unhandled | A | Capstone DSA + OOP — refactor a corrupted region of the world | — | 🔜 |

The numbering leaves room: any **A** chapter can gain a **B** before it, and any
concept that turns out too big for one B splits into `Nb` / `Nc` (as functions +
scope already do). That extensibility is the whole point of the braid.

## Concept dependency order (why this sequence)

A beginner can't hold a `for` loop over a list before they have either loops or
lists; can't write a function that returns a dict before they have both. The
order respects the real prerequisite graph:

```
variables ─▶ types ─▶ operators ─▶ conditionals ─▶ loops ─┐
                                                           ▼
                                          lists ─▶ dicts/tuples/sets ─▶ strings
                                                           │
                                                           ▼
                                              functions ─▶ scope ─▶ comprehensions
                                                           │
                                                           ▼
                                             exceptions ─▶ file I/O ─▶ classes/OOP ─▶ DSA bosses
```

## Difficulty ↔ XP ↔ stat pacing

Tie the existing XP scale (Tutorial 25 · Easy 50 · Medium 100 · Hard 200 · Boss
500) to the braid so progression *feels* like a curve:

- **B-chapter interactions** pay small XP + gold (20-ish) each, many of them —
  the learner is never starved, mirroring how 1b already works.
- **B-chapter missions** pay Tutorial/Easy — you're proving you can do the thing
  you just learned in a safe room.
- **A-chapter missions** pay Easy/Medium — same concept, now under stakes.
- **DSA bosses** pay Hard/Boss — and are the only places failure *costs* stats.

This keeps the golden rule intact: **failure in a B-chapter never costs
progress; only the marquee A-chapter trials have teeth.** See
[05_mechanics.md](05_mechanics.md#failure-that-teaches).

## What "from scratch" demands that the PRD doesn't yet list

The PRD's curriculum stops at "DSA bosses." A true from-scratch path needs three
things the roadmap should absorb explicitly:

1. **OOP.** You can't claim to teach Python and skip classes. It's also the
   perfect thematic climax (chapters 11/11b): the player graduates from *using*
   the world's objects to *defining* new ones — becoming a peer of the System.
2. **Scope**, split out of functions (7c). Beginners break on this constantly;
   it deserves its own short B.
3. **The infinite-loop curse as a taught moment**, not just a stat penalty. The
   VIT drain for infinite loops already exists — chapter 3b should *stage* it so
   the lesson is felt, not just punished. See
   [05_mechanics.md](05_mechanics.md#the-infinite-loop-curse).
