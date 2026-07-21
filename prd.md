# PyBe — Product Requirements Document

> **Version:** 1.1 · **Date:** July 21, 2026 · **Status:** Living document
>
> This document defines *what* PyBe is and *why*. For setup, deployment, API reference and file layout, see [`README.md`](README.md). For engine internals, see [`docs/`](docs/).

---

## 1. Summary

PyBe is a modular, scenario-driven Python learning engine that teaches programming through RPG narrative. Learners write real Python to solve in-world problems — initialising character stats with variables, surviving a dragon's trial with an algorithm — and progress through branching story driven by their coding proficiency.

It is architected as a **game engine, not a game**. The engine is permanent and stable; all narrative, challenges and assets load from external data files. This separation is what makes infinite content expansion possible without touching engine code, and it is the single most important constraint in the product.

---

## 2. Problem

Traditional Python instruction — video courses, textbooks, isolated exercises — fails learners in four consistent ways:

- **Low engagement.** Practice has no compelling context.
- **No sense of progression.** Advancement stops at "exercise complete."
- **Disconnected practice.** Exercises feel arbitrary and unrelated to each other.
- **No consequence.** Mistakes carry no weight, so there is little incentive to think before typing.

PyBe embeds Python education in a consequence-driven world where code is the player's primary weapon.

---

## 3. Audience

| Segment | Description |
|---|---|
| **Primary** | Beginner-to-intermediate Python learners (14+) who enjoy games. |
| **Secondary** | Educators and bootcamps wanting a gamified supplement. |
| **Tertiary** | Experienced developers wanting an RPG-flavoured fundamentals and DSA refresher. |

---

## 4. Vision and goals

> *"Abandon dry, textbook-style learning in favour of relatable, engaging, high-stakes scenarios — from fantasy RPG to slice-of-life comedy — all powered by real Python code."*

1. **Immersive learning** — every coding challenge sits inside a story beat.
2. **Engine permanence** — the core never needs modification to add content.
3. **Data-driven architecture** — stories, challenges, assets and progression live in external files.
4. **Content-creator workflow** — a non-engineer can expand the game by writing `.scene` files, adding assets and defining challenge JSON.
5. **Progressive mastery** — from variables to exception handling, file I/O and DSA, with difficulty tied to story progression.

---

## 5. Curriculum

| Phase | Topics | Example scenarios |
|---|---|---|
| **Foundations** | Variables and data types, basic I/O, operators | Character initialisation, stat assignment |
| **Control flow** | `if`/`elif`/`else`, `for`, `while` | Triage decisions, survival scenarios |
| **Core fundamentals** | Lists, tuples, dicts, strings, functions, scope, comprehensions | Inventory, NPC interactions, spell crafting |
| **Advanced core** | Errors and exceptions, file I/O | System debugging quests, scroll decryption |
| **Boss tier (DSA)** | Algorithmic challenges | Dragon Trials, boss battles |

### Learning philosophy

- **Practical application.** Learners solve in-world problems with code.
- **Fail gracefully.** Infinite loops and syntax errors produce informative in-world feedback and temporary stat drains — never permanent discouragement, never a blocked path.
- **Immediate feedback.** Execution is fast and deterministic, so logic errors surface instantly.
- **Think before you code.** The Mana system taxes blind guessing and rewards deliberate problem solving.

---

## 6. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                   │
│   HUD  ·  DialogueBox  ·  Monaco Editor  ·  Overlays         │
│   SystemPanel  ·  SceneBackground  ·  Interaction widgets    │
└──────────────────────────┬───────────────────────────────────┘
                           │  HTTP (JSON)
┌──────────────────────────┴───────────────────────────────────┐
│                  BACKEND (FastAPI + Uvicorn)                 │
│   Story loader   ·  Executor (sandbox)  ·  Player manager    │
│   Challenge      ·  Scoring engine      ·  Save system       │
│   loader         ·  Templating          ·  Content watcher   │
└──────────────────────────┬───────────────────────────────────┘
                           │  File system
      story/*.scene · challenges/*.json · interactions/*.json
      assets/ · config/ · saves/
```

**Stack:** React 19, Vite 8, Monaco Editor, Axios · Python, FastAPI, Uvicorn, Pydantic · custom `.scene` DSL and JSON.

File layout and API reference: [`README.md`](README.md).

---

## 7. Core systems

### 7.1 Story engine

A custom DSL in `.scene` files carries all narrative. The engine parses these into a beat stream and serves scenes on demand.

**Requirement:** the engine must auto-discover new `.scene` files. Adding `story/chapter_18.scene` requires zero engine modification. Tag reference lives in [`README.md`](README.md) and [`docs/03_story_language.md`](docs/03_story_language.md).

### 7.2 Challenge system

Challenges are JSON in `challenges/`, referenced by ID from scenes. Each defines a topic, difficulty, in-world description, technical instructions, required concepts, validation tests and a reward.

Four execution types:

1. **Function testing** — inject inputs into a learner-defined function, assert return values.
2. **Script variable testing** — set up globals, run the raw script, assert output variables.
3. **Variables testing** — assert the learner defined the right variables with the right types.
4. **DSA evaluation** — check I/O sets and enforce complexity limits.

**Security requirement:** learner code executes in a sandbox with restricted globals. This is sufficient for local and trusted-classroom use; public multi-user deployment requires OS-level isolation and execution timeouts (see [`README.md`](README.md#before-going-public)).

### 7.3 Interaction system

Between dialogue and full coding challenges sit **interactions** — playable beats in `interactions/*.json`, referenced by `interactive:`. They exist to keep the learner acting rather than reading: clicking chests open, sorting values into type families, predicting output.

The engine treats an interaction's `config` as opaque and hands it to a frontend **widget registry**. A new interaction type therefore needs a React component and a JSON file — no engine change. Rewards are idempotent: replaying a scene cannot farm XP.

Specification: [`docs/09_interaction_system.md`](docs/09_interaction_system.md).

### 7.4 Player templating

Authored content — dialogue, instructions, starting code, and `validation_tests` — may contain `{{player_name}}`, `{{hp}}` and similar tokens, substituted against the live player at request time.

This is a **correctness** requirement, not a flourish. A challenge that asks the learner to print their own name must expect *their* name. It is also what lets a chapter analyse the character the learner actually built rather than a hardcoded example.

### 7.5 Scoring engine

Code is evaluated across several dimensions, each mapped to an RPG stat:

| Stat | Measures | Earned by |
|---|---|---|
| **XP** ⭐ | Story progression | Challenges, bosses, side quests |
| **INT** 🧠 | Coding knowledge | Correct syntax and logic, Pythonic solutions |
| **WIS** 📚 | Code understanding | Meaningful names, readable code, right data structures |
| **DEX** ⚡ | Efficiency | Fewer lines, comprehensions, no duplication |
| **VIT** ❤️ | Persistence | Hard quests (gained); infinite loops and crashes (lost slightly) |
| **MP** 🔷 | Coding energy | 5 MP per submission; correct solutions refund it |
| **Reputation** 🌟 | NPC trust | Optional quests, helping NPCs, clean solutions |
| **Gold** 💰 | Currency | Missions and bosses — buys cosmetics, never progress |

**XP scale:** Tutorial 25 · Easy 50 · Medium 100 · Hard 200 · Boss 500.

### 7.6 Player and RPG system

**Base stats:** HP 100 · Strength 10 · Defense 10 · Dexterity 10 · Mana 50 · Stamina 100 · XP 0 · Gold 100.

**The Dragon's Judgment.** During character initialisation the engine enforces stat balance through narrative rather than validation errors:

| Condition | Outcome |
|---|---|
| Any core stat below minimum | "Blessing of the Dragon" — stats raised to base. Achievement: `DRAGON'S BLESSING` |
| All stats in range | Player keeps stats. Achievement: `DRAGON'S RECOGNITION` |
| Any stat above cap | A DSA trial. Pass → keep stats (`DRAGON CONQUEROR`). Fail → stats reset to base. |

**Failure is never a dead end.** All three judgments — and both trial outcomes — converge on Chapter 1b. A learner who fails loses the stats they over-claimed, but the story continues; the Dragon's own line, *"power without wisdom is nothing,"* sets up the Wisdom chapter directly. This is the "fail gracefully" principle in mechanical form: mistakes cost something, never progress.

### 7.7 Save system

Saves persist chapter and scene, all stats, inventory and gold, XP and level, achievements, completed missions, and story flags and choices.

Auto-save fires after every successful challenge and scene advance; manual save and load are exposed via API.

**Current scope:** one player, flat JSON on disk. Multi-user support requires sessions and a datastore — a deployment concern, not an engine redesign.

### 7.8 Asset pipeline

Media lives in `assets/` (`backgrounds/`, `characters/`, `music/`, `sound/`, `animations/`) and is referenced by filename alone from `.scene` files. The backend serves the directory directly, so adding art means dropping in a file and naming it — no build step, no import, no engine change.

Missing referenced assets are reported at startup rather than failing silently at runtime.

---

## 8. Frontend requirements

### 8.1 Design system

- **Theme:** Handcrafted Paper Fantasy — the game is a manuscript the player is writing.
- **Style:** Aged parchment, iron-gall ink, gold-leaf rules, wax seals. Paper *stacks*; it does not float. Elevation is layered shadow and pressed inset, never glass or blur.
- **Palette:** Parchment grounds (`--paper` `#f2e8d2`, `--paper-raised` `#f8f1e0`), ink text (`--ink` `#2f2418`), gold leaf for rules, wax red as primary action, moss green for success, ink-blue for the System, plum for the Sage.
- **Type:** Cinzel (display), EB Garamond (body), Fira Code (code). Serif-plus-mono contrast, never two similar sans-serifs.
- **Motion:** Exponential ease-out only (`cubic-bezier(0.22, 1, 0.36, 1)`). Paper settles; it does not spring.
- **Accessibility:** body text ≥4.5:1, focus rings ≥3:1 non-text contrast, controls ≥44px, and a `prefers-reduced-motion` fallback for every animation.

### 8.2 Layout and components

A split view: narrative panel left (story, dialogue, instructions, typewriter reveal), Monaco editor right (syntax highlighting, matching theme).

| Component | Responsibility |
|---|---|
| **HUD** | Persistent chapter, HP, Mana, XP, Gold |
| **SceneManager** | Scene lifecycle — dialogue, challenges, overlays, mode transitions |
| **DialogueBox** | NPC dialogue with typewriter effect; distinguishes NPC from System voice |
| **ChallengePanel** | Editor plus console with output, errors and pass/fail indicators |
| **DragonOverlay** | Full-screen cinematic for Dragon encounters |
| **RewardPopup** | XP, stat bonuses, achievements, titles |
| **EndScreen** | Chapter completion or game over |
| **SceneBackground** | Scene art; aspect-aware fit, push-in entrance, drift, motes |
| **SystemPanel** | The System's voice, in nine variants |

### 8.3 The System's voice

The UI has **two registers, and the contrast is the point.**

The world is handcrafted paper — parchment, ink, gold leaf, wax. Everything diegetic lives there. The System is an *overlay* on that world: dark, backlit, machine-precise panels with ornate filigree and glowing accents. The player should feel the System interrupting reality, not belonging to it.

Nine variants (`alarm`, `system`, `notification`, `skill_learned`, `status`, `warning`, `item_obtained`, `level_up`, `arrival`) are specified in [`docs/11_system_panels.md`](docs/11_system_panels.md).

Scene art appears behind **narration only** — challenges and interactive beats keep a clean page so nothing competes with the work.

---

## 9. Story content

```
                 awakening
                     │
              chapter_1_dragon
              │              │
     (overpowered)      (weak / balanced)
              │              │
   chapter_1_dragon_trial    │
        │         │          │
     (pass)    (fail)        │
        │         │          │
        │  chapter_1_trial_failed
        │         │          │
        └─────────┴──────────┘
                     │
        chapter_1b_wisdom_of_system
                     │
         chapter_2_trial_of_choice
```

**Chapter 0 — The Awakening.** Ancient ruins. Variables and data types. The player defines their character with Python; the System guides initialisation; the Dragon descends to judge.

**Chapter 1 — The Dragon's Trial.** The Dragon's domain. DSA (longest substring without repeating characters). Triggered by overpowered stats. Success earns `DRAGON CONQUEROR`; failure resets stats — and the story continues either way.

**Chapter 1b — Wisdom of the System.** The Sage's library. Variables, assignment, types, `print()`, `input()`. Both Dragon outcomes converge here. The Sage retrieves the player's *actual* character sheet and teaches them what their own values mean: variables as chests, types as four families, `print()` as the voice, `input()` as the ear. Ten interactive beats, two coding missions.

> **Design reference.** This chapter sets the standard for interaction density: the learner acts at least once every 20–30 seconds and never presses Next more than a few times in a row.

**Chapter 2 — Trial of Choice.** Control flow. An injured elder at the Gate of Choices; the player teaches the gate to decide between Fire, Water and Nature.

**Characters.** *The Player* — an amnesiac traveler summoned to master the Code. *The System* — a cold, precise digital voice managing stats and quests. *The Ancient Dragon* — a god-like judge of souls, testing ambition against experience.

---

## 10. Non-functional requirements

| Category | Requirement |
|---|---|
| **Modularity** | Engine and content strictly decoupled; new chapters need zero engine changes. |
| **Extensibility** | New features arrive as modules, not as additions to core files. |
| **Compatibility** | DSL parser updates must never break existing `.scene` files. |
| **Security** | Learner code runs sandboxed with restricted globals. |
| **Performance** | Assets cached by the loader; code execution gives immediate feedback. |
| **Configurability** | Tunables (XP, Mana costs, stat thresholds) live in config files, not constants. |
| **Observability** | Authoring errors — missing assets, unknown widgets, malformed challenges — surface at startup, not as a blank screen mid-play. |
| **Documentation** | Every new module and public API is documented in `docs/`. |

---

## 11. Design principles

1. Never hardcode story text — all narrative belongs in `.scene` files.
2. Never modify existing engine APIs unless absolutely necessary.
3. Keep the engine modular and data-driven.
4. Add features through modules; don't pollute core files.
5. Treat `.scene` files as the single source of truth for story, assets and challenges.
6. Preserve backward compatibility with older story files.
7. Prefer configuration over hardcoding.
8. Document everything; `docs/` evolves with the engine.

These are binding on human and AI contributors alike — see [`LLM_RULEBOOK.md`](LLM_RULEBOOK.md).

---

## 12. Content-creator workflow

```
1. Write a scene            →  story/chapter_X.scene
2. Add media                →  assets/backgrounds/, assets/music/, …
3. Define challenges        →  challenges/new_challenge.json
4. Launch                   →  the engine discovers everything else
```

No engine code modification. Content files are re-read while the dev server runs.

---

## 13. Roadmap

| Category | Features |
|---|---|
| **Narrative** | Multiple endings, deeper branching, NPC relationships, cutscenes, voice acting, localisation |
| **Economy** | Shops, inventory upgrades, crafting |
| **Gameplay** | Boss fights, daily quests, multiplayer challenges |
| **Platform** | Multi-user accounts, hardened execution sandbox, hosted deployment |
| **AI** | AI-generated NPC dialogue |
| **Community** | Mod support, user-created chapters |

The architecture is intended to absorb all of these without structural rewrites.

---

## 14. Success metrics

| Metric | Target |
|---|---|
| **Engagement** | Average session > 20 minutes |
| **Completion** | > 60% of players who start Chapter 0 reach Chapter 2 |
| **Learning effectiveness** | Measurable skill improvement, tracked via challenge pass rates over time |
| **Content velocity** | A new chapter authored and deployed in < 1 day with no engineering support |
| **Code quality** | Average WIS and DEX trend upward as players progress |

---

## 15. Glossary

| Term | Definition |
|---|---|
| **Scene** | A narrative unit in a `.scene` file — dialogue, assets, challenges, transitions. |
| **Beat** | A single step within a scene's parsed stream. |
| **DSL** | PyBe's custom markup for `.scene` files. |
| **Challenge** | A JSON-defined coding exercise, referenced by scenes, run by the executor. |
| **Interaction** | A lightweight playable beat rendered by a frontend widget. |
| **Dragon's Judgment** | The Chapter 0 stat-balancing mechanic. |
| **Mana (MP)** | Coding energy that gates submission spam and rewards deliberate work. |
| **Engine** | PyBe's permanent core — reads data files and orchestrates play, never contains story. |
