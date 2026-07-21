# Interaction System

Interactions are the playable beats between dialogue and full coding
challenges: clicking chests open, sorting values into type families,
predicting what `print()` will emit.

They exist because a learner who only presses **Next** is not learning. A
concept gets an interaction when it can be *shown* faster than it can be
explained, and a challenge when the learner should write real Python.

## How it fits together

```
story/*.scene          interactive: wisdom_sort_types
        │
        ▼
interactions/*.json    { "widget": "sort_types", "config": { ... } }
        │
        ▼
frontend registry      sort_types → <SortTypes config={...} />
```

The backend never knows what a widget *does*. It loads the JSON, renders any
`{{player}}` tokens, and hands `config` to the client verbatim. A new
interaction type therefore needs a React component and a JSON file — and no
engine change, per rulebook rules 3 and 4.

## Interaction file schema

`interactions/<interaction_id>.json`:

| Field | Required | Description |
|---|---|---|
| `interaction_id` | yes | Unique ID, referenced by `interactive:` in a `.scene` |
| `widget` | yes | Registry key naming the component that draws it |
| `title` | no | Heading shown above the beat |
| `prompt` | no | One-line instruction |
| `config` | no | Widget-specific payload, opaque to the engine |
| `reward` | no | `{ xp, gold, title, achievement }`, granted once |

Rewards are **idempotent**: completion is recorded in
`player.completed_missions`, so replaying a scene never farms XP.

## Registered widgets

Registry: `frontend/src/components/interactions/registry.jsx`.
The names are mirrored in `config/widgets.json`, which the backend reads to
warn at startup if a scene references a widget the UI cannot draw.

| Widget | Teaches | Config shape |
|---|---|---|
| `system_scan` | Reading a record line by line | `scan_label`, `lines: [{code, note, accent}]` |
| `reveal_chests` | A variable is a name + a value | `chests: [{name, value, caption}]` |
| `build_statement` | Assignment syntax; `=` vs `==` | `slots`, `slot_labels`, `fragments: [{id, text, slot, wrong_hint}]`, `success` |
| `value_dial` | Reassignment replaces | `variable`, `initial`, `target`, `min`, `max`, `success` |
| `sort_types` | str / int / float / bool | `bins: [{id,label,hint}]`, `items: [{id,text,bin,reveal}]` |
| `predict_output` | `print()`, quotes, `input()` | `rounds: [{code, options, answer, explain}]` |

## Widget contract

Every widget receives exactly two props:

```jsx
<Widget config={interaction.config} onSolved={fn} />
```

- `config` — the JSON payload, already player-rendered.
- `onSolved()` — call **once**, when the learner has genuinely completed the
  beat. `InteractionStage` handles the reward call, the XP flourish and the
  Continue button; a widget never talks to the API itself.

Two rules hold across all of them:

1. **Never block progress on being right the first time.** A wrong answer
   shakes, explains itself, and lets the learner continue — the PRD's "fail
   gracefully" principle. Interactions teach; challenges assess.
2. **Tap-to-place, not HTML5 drag-and-drop.** It works on touch, works from
   the keyboard, and cannot strand a token mid-drag.

## Adding a new interaction

1. Write `interactions/my_beat.json`.
2. If it needs a new widget: add the component, register it in
   `registry.jsx`, and add its key to `config/widgets.json`.
3. Reference it from a scene: `interactive: my_beat`.
4. Restart the backend — files are auto-discovered.
