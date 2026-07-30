# Mechanics — Turning Game Systems into Teaching Tools

The engine already has the systems (stats, MP, the Dragon's Judgment, scoring,
rewards, interactions, a planned shop and battles). This file is about *pointing
them at the curriculum* so a mechanic isn't just flavor — it teaches or
reinforces a specific Python idea.

## The stats already map to coding virtues — commit to it

The scoring engine grants INT/WIS/DEX/VIT for real code qualities. Make the
mapping *legible* to the learner so they understand what each stat is telling
them about their code:

| Stat | Coding virtue | Make it teach by… |
|---|---|---|
| **INT** 🧠 | correctness / logic | awarding on passing tests + Pythonic constructs |
| **WIS** 📚 | readability | rewarding meaningful names, right data structure (dict over parallel lists) |
| **DEX** ⚡ | efficiency | rewarding comprehensions, fewer lines, no duplication — the *whole point* of chapter 10 |
| **VIT** ❤️ | resilience | gained on hard clears; drained by infinite loops / crashes |
| **MP** 🔷 | deliberation | 5 MP per submit; refunded on success; drained by guessing |

**Design move:** after a successful mission, the RewardPopup should say *which
virtue* went up and *why* ("+3 WIS — you named your variables well"). The stat
becomes feedback on *how* they coded, not just *that* they passed. That's the
professor's rubric, gamified.

## MP is the "think before you code" mechanic — use it to teach it

MP (5 per submission, refunded on success, drained on blind guessing) is already
the anti-spam system. Lean into it pedagogically:

- Show remaining MP on the ChallengePanel so the cost is visible *before* submit.
- On a wasteful failure (e.g. obvious syntax error, or resubmitting identical
  code), narrate it: "The System sighs. −5 MP. *Read the error first.*"
- Low MP shouldn't hard-block — it should *slow* you and nudge you to the hints,
  which teaches error-reading instead of guess-and-check. Keep it a teacher, not
  a wall (fail gracefully).

## Failure that teaches

The golden rule from the PRD: **mistakes cost something, never progress.** Turn
each failure mode into a lesson:

| Failure | Current | Teaching upgrade |
|---|---|---|
| Wrong answer in an **interaction** | shake + explain | keep — this is already right |
| Failed **B-chapter mission** | retry | add a targeted hint that names the misconception |
| Failed **DSA boss** (Dragon Trial) | stat reset, story continues | keep — the one place with teeth, and it *still* routes to the teaching chapter |
| **Infinite loop** | slight VIT drain | stage it as a taught moment ↓ |

### The infinite-loop curse

The VIT penalty for infinite loops already exists but is invisible. Chapter 3b
(loops) should *stage* it: the Warden of the Echoing Halls is a man **stuck in a
`while True:` with no `break`** — living proof. The learner's mistake (an
infinite loop) briefly traps their *own* avatar in the corridor animation, drains
a little VIT, and the Warden says "Now you feel it. Give the loop a way *out*."
The penalty becomes the lesson. Requires: an execution timeout in the sandbox
(see [07_future_building.md](07_future_building.md)) — which the game needs anyway.

## The Dragon's Judgment is a reusable pattern, not a one-off

Chapter 0's judgment (weak → blessing, balanced → recognition, overpowered →
trial) is a lovely mechanic. Generalize it: **any A-chapter can gate on the
*shape* of the player's solution, not just pass/fail.** Examples:

- Solve chapter 10's duel with a `for` loop → you pass, "adequate." Solve it with
  a comprehension → bonus DEX + a cosmetic. The *style* of the answer branches
  the reward, exactly like stat-balance branches Chapter 0.
- A boss that reads WIS: messy-but-correct code opens the door slowly; clean code
  opens it with a flourish and extra reputation.

This makes "write it *well*, not just *right*" a mechanic, which is the hardest
thing to teach a beginner.

## Battles as timed code (from the RPG doc) — scoped for teaching

The RPG doc promises "turn-based combat where spells are executed by writing
small snippets within time limits." Make battles the **A-chapter application**
of whatever the last B taught:

- After 7b (functions): a battle where each "spell" is *calling a function you
  defined* with different arguments — reuse under pressure.
- After 5b (dicts): an enemy with a weakness table (a dict); you `.get` the right
  counter-element each turn.
- Keep the time limit *generous* and non-punishing early (fail gracefully);
  tighten only at boss tier. Battles reinforce; they don't gate learning.

## The shop and cosmetics teach nothing — and that's correct

Gold buys **cosmetics only** (skins, pets, spell animations) — never progress.
Protect this. The teaching value of the shop is indirect but real: it gives Gold
(and therefore clean, efficient code, which earns Gold) a *point*, without ever
letting a learner buy their way past a concept. Reputation unlocks secret
merchants / side quests — good place for **optional extra practice** framed as
bonus content rather than remediation.

## Widget proposals

New interaction widgets the B-chapters want. Each is a React component + a
`config/widgets.json` entry + JSON files — **no engine change** (per the
interaction contract). Listed with the config shape an author would fill.

| Widget | Teaches | Config sketch |
|---|---|---|
| `balance_scale` | comparison operators | `{ left, right, op_options, answer }` — drop two values, pick the operator that's true |
| `loop_stepper` | loop iteration & accumulation | `{ init, body, condition, steps:[{i, state}] }` — tap Step, watch counter/accumulator |
| `index_picker` | list indexing, 0-based, out-of-range | `{ items, ask_index, allow_out_of_range }` |
| `key_lookup` | dict access by key | `{ pairs:[{key,value}], ask_key }` |
| `ribbon_slicer` | string slicing | `{ text, target_slice }` — drag `[start:stop]` handles |
| `call_trace` | functions: input→return, reuse | `{ signature, calls:[{args, returns}] }` |
| `ward_catch` | try/except matching | `{ throws:"ValueError", except_options, answer }` |
| `collapse_lines` | comprehensions | `{ loop_fragments, target_comprehension }` |
| `blueprint_forge` | classes/instances/state | `{ fields, instances:[{name, values}] }` |

Build them in roughly curriculum order; each unblocks one B-chapter. Priority
order and effort in [07_future_building.md](07_future_building.md).

## One reusable widget beats three specific ones

Before building a new widget, check whether `predict_output` (rounds of
code→choose-the-output), `sort_types` (bucket things by category), or
`build_statement` (assemble code from fragments) already covers it. Half the
list above is genuinely new interaction *shapes*; the other half could be
`predict_output` rounds with good copy. Author the JSON version first; only build
a component when the interaction *shape* is truly new. (Lazy on purpose — a new
component is the expensive path.)
