# Story Language (DSL)

To separate engine logic from story content, PyBe uses a custom lightweight DSL (Domain Specific Language) stored in `.scene` files.

## Tags and Syntax
The engine must parse the following tags:

- `@scene [id]`: Declares the start of a new scene and its unique ID.
- `background: [file]`: Sets the background image. May appear **more than once** in a scene — the first is the opening image, each later one changes location mid-scene. See [10_background_art.md](10_background_art.md).
- `music: [file]`: Sets the background music track.
- `npc [Name]:`: Initiates dialogue spoken by an NPC. Characters are shown through the scene background, not as cut-out portraits — switch to their art with `background:` when they enter.
- `system [variant]:`: Renders a System UI panel. First quoted line is the title, the rest is the body. See [11_system_panels.md](11_system_panels.md).
- `dialogue:`: Standard narration or dialogue.
- `choice:`: Presents branching options to the player.
- `mission: [challenge_id]`: Triggers a coding challenge (loads from `challenges/[challenge_id].json`).
- `interactive: [interaction_id]`: Plays an interactive beat (loads from `interactions/[interaction_id].json`). See [09_interaction_system.md](09_interaction_system.md).
- `battle:`: Initiates a combat sequence.
- `reward:`: Grants XP, items, or titles.
- `achievement: [name]`: Unlocks a specific badge.
- `condition:`: Evaluates a state before proceeding (e.g., checking stats).
- `next: [scene_id]`: The scene ID to load after this one concludes.

## Beats: authored order is playable order

A scene parses into an ordered **beat stream** (`ParsedScene.beats`). Every
`dialogue:`, `npc:`, `mission:`, `interactive:` and `background:` block becomes
one beat, in the order written. The client plays them in sequence, so a chapter can
teach → play → teach → test inside a single scene.

Two consequences worth knowing:

- **A scene may contain more than one `mission:`.** Chapter 1b uses two.
  (The older `scene.mission` field still reports the *first* mission only,
  for backward compatibility; anything new should read `beats`.)
- Consecutive dialogue blocks are merged by the client into a single
  typewriter run, so prose still flows under one "Next".

## Player templating

Any authored string may contain `{{token}}` placeholders, substituted against
the live player when the scene is requested:

```text
npc Dragon:
"Power alone cannot shape destiny, {{player_name}}."
"You carry {{hp}} health and {{strength}} strength."
```

Available tokens: `player_name`, `class`, `class_name`, `hp`, `strength`,
`defense`, `dexterity`, `mana`, `stamina`, `xp`, `gold`, `level`,
`intelligence`, `wisdom`.

Templating also applies to challenge and interaction JSON — including
`validation_tests`, so a challenge can expect the learner's *own* name as
output. An unknown token is left visible (`{{oops}}`) rather than blanked, so
typos surface instead of silently vanishing. Implemented in
`backend/app/engine/templating.py`.

## Examples

### Basic Narrative and Challenge
```text
@scene awakening

background: ruins.png
music: awakening.mp3

npc System:
"Welcome, Unknown Traveler."
"Identity Required."
"Please initialize your character."

mission:
variables_intro

reward:
xp: 20
title: Awakened One

next:
dragon_trial
```

### Conditional Branching Example
```text
@scene dragon_trial_results

condition: hp >= 100 AND strength >= 10 AND hp <= 500
next: dragon_recognition

condition: hp > 500 OR strength > 100
next: overpowered_dragon_trial

condition: hp < 100 OR strength < 10
next: weak_dragon_blessing
```

The parser must be modular and easy to extend if new tags are needed in the future.
