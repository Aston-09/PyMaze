# PyBe — Design Brainstorm

> Forward-looking design notes for where the game and the curriculum go next.
> These are **proposals**, not the PRD. The PRD says what PyBe *is*; this folder
> explores what it could *become*. Nothing here is binding until it lands in
> `story/`, `challenges/`, `interactions/` or the docs.

Written from two chairs at once: an **RPG systems designer** (what makes the next
hour worth playing) and a **Python professor** (what makes the next concept
actually stick). Every idea has to earn both.

---

## The one idea everything else hangs on: the A/B braid

The story so far already discovered the game's core rhythm without naming it.
Name it, and it becomes a machine you can crank forever.

- **A-chapters — story.** Plot moves. A new place, a character, stakes, usually
  **one** mission. The player *applies* what they know against real consequence.
  Interaction density is low; narrative density is high. (Ch 0, Ch 1, Ch 2.)
- **B-chapters — teaching.** Plot *pauses* inside a "safe pocket" (the Sage's
  Library). One concept cluster gets taught deeply — many interactions, a couple
  of missions, the learner acting every 20–30s. Narrative barely moves; skill
  moves a lot. **Chapter 1b is the reference implementation.**

The braid is: **A poses a problem the player can't solve → B teaches the tool →
A returns and makes them use it under pressure.** Teach, then test, then apply.
That is simultaneously good pedagogy (concept before application) and good game
design (setup before payoff). Skateboard the whole game on it.

```
A: Awakening ──▶ A: Dragon ──▶ B: Wisdom of the System ──▶ A: Trial of Choice ──▶ B: ... ──▶ A: ...
   (variables)     (judgment)     (vars·types·io deeply)      (if/elif/else)
   problem          stakes          TEACH                       APPLY
```

Full mapping in [01_curriculum_map.md](01_curriculum_map.md).

---

## The metaphor spine

The story already teaches through **consistent physical metaphors**, and they're
good. Keep extending the *same* visual language instead of inventing a new one
per concept — a returning player should recognise a chest and know it means
"variable" three chapters later.

| Concept | Established / proposed metaphor |
|---|---|
| Variable | a **chest** — name on the lid, value inside ✅ |
| Data types | the **four families** (str/int/float/bool), four orbiting runes ✅ |
| `print()` | the **silver mirror** — the world hears you ✅ |
| `input()` | the **listening crystal** — the world answers ✅ |
| `if/elif/else` | the **Gate of Choices** ✅ |
| Operators | the **Alchemist's scales** — combine and weigh values *(proposed)* |
| Loops | the **Echoing Halls** — repeat until released; infinite loop = the curse *(proposed)* |
| Lists | the **numbered satchel** — ordered slots, counting from 0 *(proposed)* |
| Dict | the **card catalogue / grimoire** — a name maps to a thing *(proposed)* |
| Functions | the **spellbook** — bind an incantation once, cast it forever *(proposed)* |
| Exceptions | **wards** against corruption — `try` a dangerous spell, `except` catches the blast *(proposed)* |
| Classes / OOP | the **Loom of Creation** — stop using the world's beings, start defining them *(proposed)* |

Metaphors are cheap to author (they live in `.scene` and `.json`) and they are
the single biggest reason Chapter 1b works. Detail in
[04_b_chapters.md](04_b_chapters.md).

---

## Files in this folder

| File | What it covers |
|---|---|
| [01_curriculum_map.md](01_curriculum_map.md) | The full Python-from-scratch progression braided into story acts — the backbone |
| [02_story_arc.md](02_story_arc.md) | The overarching plot: why the player is here, the antagonist, the ending |
| [03_characters.md](03_characters.md) | The cast, their teaching domains, and *when* each is introduced |
| [04_b_chapters.md](04_b_chapters.md) | How to design teaching chapters — the template behind the Sage's Library |
| [05_mechanics.md](05_mechanics.md) | Turning stats, MP, battles, the shop and new widgets into teaching tools |
| [06_achievements.md](06_achievements.md) | An achievement catalogue tied to learning milestones and mastery |
| [07_future_building.md](07_future_building.md) | Systems and content to build, roughly in order |

## The three rules a new idea must pass

1. **Does it teach a real Python idea, or just decorate one?** Cut decoration.
2. **Could a non-engineer author it in `.scene` + `.json`?** If it needs engine
   surgery, it's a *future_building* item, not a chapter — keep them separate.
3. **Does the learner act, or just read?** If they only press Next, it's a
   cutscene, not a lesson.
