# B-Chapters — Designing the Teaching Modules

The "b type" chapters you asked about. Chapter 1b (Wisdom of the System) already
nailed the form; this file reverse-engineers *why it works* into a repeatable
template, then catalogues the B-chapters to build.

## Why Chapter 1b works (the anatomy to copy)

Read `story/chapter_1b_wisdom_of_system.scene` and the pattern is exact:

1. **A safe pocket outside the plot.** The Sage's Library is *nowhere* — "every
   soul that passes the Dragon arrives here." Removing plot stakes is what lets
   the learner fail freely. A B-chapter needs its own pocket dimension / room /
   mentor's domain.
2. **One concept cluster, taught as numbered lessons.** 1b runs `— LESSON I —`,
   `— LESSON II —` … Each lesson = one idea + one metaphor + one interaction.
3. **Show before tell, act before read.** Every idea gets an *interaction*
   before it gets a *mission*. The chest is opened before "variable" is defined.
4. **A metaphor per idea, drawn from the same visual language** (chests, four
   families, mirror, crystal). The metaphor does the cognitive lifting.
5. **Interaction density ≥ one action / 20–30s.** 1b has **ten** interactions
   and **two** missions. The learner never presses Next more than a few times.
6. **Two missions per cluster: a "prove it" then a "combine it."** 1b:
   `wisdom_voice_of_system` (just `print`) then `wisdom_listener_of_worlds`
   (`input` + variable + `print` together).
7. **A closing recall.** `wisdom_final_recall` makes the learner reassemble
   everything in one breath before the door opens. Every B ends with a recall.
8. **Failure never blocks.** Interactions shake, explain, and let you continue
   (per [docs/09_interaction_system.md](../docs/09_interaction_system.md)).

## The B-chapter template

A reusable skeleton any author can fill. Ordered as a `.scene`:

```
@scene chapter_Nb_<name>
background: <mentor's domain>
music: <calm teaching theme>

# 1. ARRIVAL — enter the safe pocket, meet/greet the mentor
npc <Mentor>: "<welcome + name the skill about to be learned>"
system skill_learned: "MODULE UNLOCKED / <Cluster> / <sub-topics>"

# 2. For each idea in the cluster:
dialogue: "— LESSON <n> — <TITLE> —"
npc <Mentor>: "<the metaphor, stated physically>"
interactive: <show-the-idea beat>      # act before read
npc <Mentor>: "<the idea named in Python terms>"

# 3. PROVE IT — one small mission using the newest idea alone
mission: <cluster>_prove

# 4. COMBINE IT — one mission using the whole cluster together
mission: <cluster>_apply

# 5. RECALL — reassemble everything, then the exit
interactive: <cluster>_final_recall
system level_up: "CHAPTER COMPLETE / <cluster mastered>"
reward: { xp, gold, achievement }
next: chapter_<N+1>_<story>
```

Rule of thumb per B-chapter: **4–6 lessons, 6–10 interactions, 2 missions, 1
recall.** More than that and split into `Nb`/`Nc` (as functions+scope do).

## Interaction budget = the quality bar

The single measurable target for a B-chapter: **the learner acts at least once
every 20–30 seconds.** If a stretch of scene has three `dialogue:` blocks in a
row with no `interactive:` or `mission:`, that's a defect, not a style choice.
Count actions when reviewing a B draft.

## Catalogue of B-chapters to build

Each entry: the pocket, the metaphors, the lessons, and which **new widgets** it
wants (widget specs live in [05_mechanics.md](05_mechanics.md#widget-proposals)).

### 2b — The Alchemist's Scales (Operators)
- **Pocket:** an alchemist's tower of balances and reagents.
- **Lessons:** arithmetic (`+ - * / // % **`) as mixing; comparison (`== != < >`)
  as weighing on a balance; logical (`and/or/not`) as combining wards; precedence
  as reagent order.
- **Metaphor payoff:** `=` *pours* into a chest; `==` *weighs* two chests. The
  most common beginner bug, taught physically.
- **Widgets:** `value_dial` (reuse), new **`balance_scale`** (drop two values,
  see which way it tips → comparison), **`predict_output`** (reuse for precedence).

### 3b — The Echoing Halls (Loops)
- **Pocket:** a cursed corridor that repeats; the Warden is trapped in it.
- **Lessons:** `for` over a known set (marching numbered stones); `range`;
  `while` + condition (a door open until the condition fails); accumulation;
  `break`/`continue`; **the infinite-loop curse** (see [05](05_mechanics.md#the-infinite-loop-curse)).
- **Metaphor payoff:** freeing the Warden *is* writing the exit condition.
- **Widgets:** new **`loop_stepper`** (watch a counter/accumulator advance one
  iteration at a time, tap Step), `predict_output`.

### 4b — The Satchel of Many Slots (Lists)
- **Pocket:** the Quartermaster's stores.
- **Lessons:** ordered slots numbered **from 0**; indexing; negative index;
  slicing; `append`/`pop`/`len`; iterating a list.
- **Metaphor payoff:** off-by-one taught by a man who counts from zero and yells
  when you don't.
- **Widgets:** new **`index_picker`** (a row of numbered pockets; tap the index,
  see what's inside; deliberately trip out-of-range once, safely).

### 5b — The Card Catalogue (Dicts, Tuples, Sets)
- **Pocket:** the blind Cataloguer's infinite archive.
- **Lessons:** dict as key→value ("find by *name*, not position"); `.get`;
  keys/values/items; tuples as **sealed scrolls** (can't change); sets as the
  **unrepeating roster** (callback to the Dragon Trial's "no two souls the same").
- **Widgets:** `sort_types` (reuse for mutable vs immutable), new
  **`key_lookup`** (type/tap a key, the drawer opens to its value).

### 6b — The Loom of Words (Strings)
- **Pocket:** the Riddle Weaver's loom.
- **Lessons:** string indexing/slicing (a ribbon of runes); `f`-strings (weaving
  a value into a sentence); `.split/.join/.strip/.upper/.lower`; immutability.
- **Widgets:** new **`ribbon_slicer`** (drag slice handles over a rune ribbon,
  see `s[2:5]` light up), `predict_output`.

### 7b — The Spellbook (Functions) + 7c — The Private Workshop (Scope)
- **Pocket:** the lazy Enchanter's study; then a back room (scope).
- **7b lessons:** `def` binds a spell once; parameters = reagents; arguments vs
  parameters; `return` = the gift; default args.
- **7c lessons:** local vs global — what's whispered in the workshop stays there;
  why reading a global works but assigning surprises you.
- **Widgets:** new **`call_trace`** (call the same spell with different arguments,
  watch inputs → return; the "write once, reuse" payoff visualized).

### 8b — The Warder's Circle (Exceptions)
- **Pocket:** the edge of a Blighted zone, inside a ward.
- **Lessons:** why an uncaught error crashes the world (the Blight itself);
  `try/except`; exception types; `else`/`finally`; raising your own.
- **Metaphor payoff:** the monster and the lesson are the same thing — you learn
  to *catch* what's been consuming the world.
- **Widgets:** new **`ward_catch`** (a spell throws an error; tap to wrap it in a
  ward and choose the matching `except`), `predict_output`.

### 9b — The Scribe's Desk (File I/O)
- **Pocket:** the Eternal Archive.
- **Lessons:** `open`, read, write, `with`; lines; the first *permanent* action —
  writing your own name into the world's record.
- **Widgets:** reuse `system_scan` (read a scroll line by line); missions do the
  real read/write.

### 10b — The Single Incantation (Comprehensions) *(short)*
- **Pocket:** the Duelist's arena.
- **Lessons:** collapse a loop to one line; list/dict/set comprehensions; when
  *not* to. Scored on **DEX**.
- **Widgets:** new **`collapse_lines`** (drag a 4-line loop's fragments into one
  comprehension; the DEX flourish).

### 11b — Blueprints of the Real (OOP) *(the capstone B)*
- **Pocket:** the Loom of Creation; the First Traveler / Architect teaches.
- **Lessons:** `class` as blueprint; `__init__`; attributes; methods; `self`;
  making instances; a first taste of inheritance. The player *defines a being*
  and it walks off the page to fight beside them.
- **Widgets:** new **`blueprint_forge`** (fill a class's fields, stamp instances,
  see two objects share a blueprint but hold different state — the core OOP
  insight, visual).

## Author checklist for any new B-chapter

- [ ] Safe pocket established; plot stakes removed.
- [ ] 4–6 numbered lessons, each: metaphor → interaction → Python name.
- [ ] Interaction budget met (action every 20–30s).
- [ ] Exactly two missions: "prove it" then "combine it."
- [ ] A closing recall interaction.
- [ ] Every referenced widget exists in `config/widgets.json`.
- [ ] Failure never blocks progress anywhere in the chapter.
- [ ] Rewards set; `next:` points at the following **A**-chapter.
