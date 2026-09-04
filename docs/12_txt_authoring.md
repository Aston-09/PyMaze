# One-File Scenario Authoring (`@challenge`)

A playable chapter normally costs two files in two directories and two syntaxes:
the narrative in `story/*.scene` (DSL) and its coding problem in
`challenges/*.json` (JSON). This document freezes the format that lets the
problem statement live in the **same text file** as the scene that triggers it.

One new top-level block, `@challenge`, sits beside `@scene`. Every construct
inside it copies a construct the `.scene` parser already understands — see
[03_story_language.md](03_story_language.md) for the scene half of the grammar
and [04_challenge_system.md](04_challenge_system.md) for what the engine does
with a challenge once it is loaded.

## Which file goes where

- **`.scene` and `.txt` are parsed identically.** The extension carries no
  meaning. A `.txt` may hold pure narrative; a `.scene` may hold a
  `@challenge`. Use `.txt` when a scenario is self-contained and `.scene` when
  extending the existing chapter spine — convention, not a rule.
- **Both suffixes live in `story/`.** Nothing new goes anywhere else.
- **`challenges/*.json` remains fully supported.** The existing JSON challenges
  keep working untouched; inline authoring is additive. A challenge defined
  inline wins over a JSON file of the same `challenge_id` — the file you are
  editing is the one you meant.
- A scene reaches a challenge exactly as before, with `mission: [challenge_id]`.
  Whether that id resolves to an inline block or a JSON file is invisible to the
  scene.

## The `@challenge` block

`@challenge [id]` declares the start of a challenge and its unique
`challenge_id`, the same way `@scene [id]` declares a scene. Everything until
the next `@scene` or `@challenge` belongs to it.

| Line | Sets | Form |
|---|---|---|
| `@challenge [id]` | `challenge_id` | Block header, mirrors `@scene` |
| `topic:` `difficulty:` `title:` | `topic`, `difficulty`, `title` | Scalar on one line, mirrors `background:` |
| `narrative:` | `narrative` | Following quoted lines, joined with newlines; mirrors `dialogue:` |
| `instructions:` | `instructions` | Following quoted lines, joined with newlines; mirrors `dialogue:` |
| `hints:` | `hints` | Following quoted lines, kept as a list; mirrors `dialogue:` |
| `code:` | `starting_code` | Following **raw** lines, verbatim and unquoted — indentation preserved |
| `tests:` | `validation_tests` | Following `input -> expected` lines; mirrors the `choice:` arrow form |
| `variables:` | `expected_variables` | Following `name: type` lines; mirrors the `reward:` key-value block |
| `reward:` | `reward` | Following `key: value` lines; identical to the scene `reward:` block |

`difficulty` is a free string, but the UI styles only `tutorial`, `easy`,
`medium`, `hard` and `boss`.

`code:` is the one section whose body is **not** quoted. Its lines are taken
verbatim so Python indentation survives, and the block ends at the next
column-0 section keyword.

### Where a section ends

A section ends at the next section keyword at column 0 — **never at a blank
line**. Space out a long `narrative:` into paragraphs, group `tests:` cases,
or put a gap before `reward:`; nothing is lost either way.

Two consequences worth knowing:

- Starter code that assigns something section-shaped (`title = "The Hobbit"`,
  `tests = []`) is still code. Only a keyword followed by a colon ends a block.
- A single-line value may go on the tag line itself — `narrative: "One line."`
  is the same as putting the quoted line beneath it, matching how `mission:`
  and `next:` already work in the scene DSL.

## The `test:` line

One `test:` line collapses four fields into one. `test_type` is exactly one of
`function`, `script_variable`, `variables`, `script_output` — there is no fifth
type.

| Written | `test_type` | Other fields set |
|---|---|---|
| `test: function sort_takings` | `function` | `function_name = "sort_takings"` |
| `test: variables` | `variables` | reads the `variables:` block into `expected_variables` |
| `test: variables stats` | `variables` | + `applies_stats = True` |
| `test: script in=nums out=total` | `script_variable` | `input_variable = "nums"`, `output_variable = "total"` |
| `test: output in=name` | `script_output` | `input_variable = "name"` |

What each type does at run time:

- **`function`** — the learner defines a function; the engine calls it once per
  test case and compares the return value.
- **`script_variable`** — the engine injects `input_variable` into the script's
  globals, runs the learner's raw script, then reads `output_variable` back out.
  Never assign the injected name in `code:` — the starter code would shadow
  every test case after the first, and startup validation flags it.
- **`variables`** — no test cases; the learner declares raw variables and each
  name in the `variables:` block is checked for its declared type.
- **`script_output`** — the engine injects `input_variable`, runs the script,
  and compares captured **stdout** against the expected value.

`test: variables stats` is reserved for character creation: it writes the
learner's variables onto the player and triggers the Dragon's Judgment. Ordinary
type drills use plain `test: variables` so they do not re-roll stats.

## The `tests:` block

Each line is `<json> -> <json>`. Both sides are parsed as JSON and stored as
`{"input": left, "expected": right}` — the exact shape
`challenges/dragon_trial.json` already uses.

```text
tests:
"abcabcbb" -> 3
"" -> 0
5 -> [1, 2, 3, 4, 5]
```

> **Porting a JSON challenge that used `expected_output`.** The arrow form
> always emits the key `expected`, never `expected_output`. This works for every
> test type — `script_output` reads
> `test.get("expected_output", test.get("expected", ""))`
> (`backend/app/engine/sandbox.py:296`), so it falls back to `expected` — but if
> you are transcribing a JSON challenge that spelled the key `expected_output`,
> know that the arrow line produces `expected` instead. Do not hand-write
> `expected_output` into an inline challenge; there is no syntax for it and none
> is needed.

### The double-bracket rule

**A list input spreads as positional arguments.** The sandbox calls the
learner's function with `fn(*test_input)` whenever the input is a list, and with
`fn(test_input)` otherwise (`backend/app/engine/sandbox.py:174`). The brackets
are therefore how you say *how many parameters the function takes*:

| Function | Test line | Engine calls |
|---|---|---|
| `def sort_takings(coins)` — **one list** | `[[3, 1, 2]] -> [1, 2, 3]` | `sort_takings([3, 1, 2])` |
| `def add_three(a, b, c)` — **three numbers** | `[3, 1, 2] -> 6` | `add_three(3, 1, 2)` |
| `def longest(s)` — one string | `"abcabcbb" -> 3` | `longest("abcabcbb")` |

Writing `[3, 1, 2] -> [1, 2, 3]` for a one-parameter function raises
`TypeError: takes 1 positional argument but 3 were given`. The outer brackets
are the argument list; the inner brackets are the argument.

This is not new behaviour — it mirrors how the JSON challenges already work.

## The `variables:` block

Only read when `test:` is a `variables` form. Each line is `name: type`, where
`type` is the Python type name reported by `type(value).__name__`:

```text
test: variables

variables:
player_name: str
hp: int
```

`bool` is a subclass of `int` but is compared by name, so `hp = True` fails an
`int` check.

## The `reward:` block

Identical to the scene `reward:` block. All four keys are optional:

```text
reward:
xp: 100
gold: 50
title: Ledger Keeper
achievement: LEDGER KEEPER
```

## Field reference

Every field the format can set, and where it is defined in
`backend/app/models/challenge.py`:

| Authored as | Field | Defined at |
|---|---|---|
| `@challenge [id]` | `challenge_id` | `challenge.py:16` |
| `topic:` | `topic` | `challenge.py:17` |
| `difficulty:` | `difficulty` | `challenge.py:18` |
| `title:` | `title` | `challenge.py:19` |
| `narrative:` | `narrative` | `challenge.py:20` |
| `instructions:` | `instructions` | `challenge.py:21` |
| `code:` | `starting_code` | `challenge.py:22` |
| `test:` | `test_type` | `challenge.py:25` |
| `test: function [name]` | `function_name` | `challenge.py:26` |
| `test: script in=` / `test: output in=` | `input_variable` | `challenge.py:27` |
| `test: script out=` | `output_variable` | `challenge.py:28` |
| `variables:` | `expected_variables` | `challenge.py:31` |
| `test: variables stats` | `applies_stats` | `challenge.py:36` |
| `tests:` | `validation_tests` | `challenge.py:38` |
| `hints:` | `hints` | `challenge.py:39` |
| `reward:` | `reward` | `challenge.py:40` |
| `reward:` → `xp:` | `ChallengeReward.xp` | `challenge.py:8` |
| `reward:` → `gold:` | `ChallengeReward.gold` | `challenge.py:9` |
| `reward:` → `title:` | `ChallengeReward.title` | `challenge.py:10` |
| `reward:` → `achievement:` | `ChallengeReward.achievement` | `challenge.py:11` |

Nothing outside this table is authorable. A name that is not a
`ChallengeDefinition` field is not a field.

## Worked example

The complete contents of `story/example_merchant.txt` — one scene and the
challenge it triggers, in one file:

```text
@scene marketplace

background: green_valley.jpg

dialogue:
"The merchant blocks your path."

npc Merchant:
"Sort my takings, traveler, and the road is yours."

mission: merchant_ledger

reward:
xp: 100
gold: 50


@challenge merchant_ledger

topic: Lists
difficulty: easy
title: The Merchant's Ledger
test: function sort_takings

narrative:
"The merchant slams a ledger down."
"Numbers scatter across the page in no order at all."

instructions:
"Write `sort_takings(coins)` that returns the coins sorted"
"from smallest to largest."

code:
def sort_takings(coins):
    # Your solution here
    pass

tests:
[[3, 1, 2]] -> [1, 2, 3]
[[]] -> []
[[5]] -> [5]

hints:
"Python lists have a .sort() method."
"Or use the built-in sorted()."

reward:
xp: 100
gold: 50
achievement: LEDGER KEEPER
```

`sort_takings` takes one parameter, so every test input is double-bracketed.

The example scene is deliberately **not** reachable from the story spine — no
chapter routes to `marketplace`, and it declares no `next:`. It is a format
fixture, not a chapter.
