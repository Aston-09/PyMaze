# Plan 01 — One-File Scenario Authoring (`.txt` → scene + problem statement)

**Goal:** Drop a single `.txt` file into `story/`. The engine parses it and produces both the playable scenario *and* its problem statement, with no other file to touch.

**Status:** Not started
**Created:** 2026-09-04

---

## Phase 0 — Documentation Discovery (COMPLETE — read before Phase 1)

Executed directly against the repo. Every claim cites the file it came from. No API below is assumed; all were read.

### Sources consulted

| File | What it told us |
|---|---|
| `backend/app/engine/story_loader.py` (1-278) | The `.scene` DSL parser. Line-based, tag-driven, `@scene`-split at L22. |
| `backend/app/engine/challenge_loader.py` (1-130) | Loads `challenges/*.json` → `ChallengeDefinition`; `validate_challenges()` at L69 catches authoring bugs at startup. |
| `backend/app/models/scene.py` | `ParsedScene`, `SceneBeat`, `SceneReward`, `SceneCondition`. |
| `backend/app/models/challenge.py` | `ChallengeDefinition` — the exact target schema. |
| `backend/app/engine/content.py` | `ContentStore` hot-reload, keyed on `(dir, suffixes, loader)`. |
| `backend/app/engine/executor.py` | `execute_and_test()` — the 4 test types. |
| `backend/app/engine/sandbox.py` (1-200) | `_call()`: **a list input spreads as positional args**. |
| `backend/app/main.py` (60-113, 225-320) | Content wiring L72-79, `/api/scene/{id}` L225, `/api/execute` L310. |
| `backend/test_content.py` | Content integrity harness — walks the spine, catches orphans. |
| `docs/03_story_language.md` | Authoritative DSL tag list. |
| `docs/04_challenge_system.md` | Challenge JSON contract. |
| `story/chapter_0_awakening.scene`, `challenges/variables_intro.json`, `challenges/dragon_trial.json` | Real authored examples to copy from. |

### The finding that shapes this plan

**The `.txt` format already exists — it is called `.scene`.** `story_loader.py` is a working line-based text parser over 18 authored chapters. `docs/01_project_overview.md` already states the goal: *"the author should only need to write new `.scene` files … and write challenge JSONs."*

The actual gap is **file fan-out**. One playable chapter costs three files in three directories across two syntaxes:

```
story/chapter_1_dragon.scene       ← narrative        (DSL)
challenges/dragon_trial.json       ← problem stmt     (JSON, ~45 lines)
interactions/*.json                ← optional widgets (JSON)
```

So this is **not** "build a story parser." It is: *let the problem statement live in the same text file as the scene that triggers it.*

### Allowed APIs (verified to exist — do not invent beyond these)

```python
# story_loader.py
parse_scene_file(filepath: str) -> List[ParsedScene]
load_all_scenes(story_dir: str) -> Dict[str, ParsedScene]

# challenge_loader.py
load_all_challenges(challenges_dir: str) -> Dict[str, ChallengeDefinition]
validate_challenges(challenges: Dict[str, ChallengeDefinition]) -> List[str]

# models/challenge.py — ChallengeDefinition fields, exactly:
challenge_id, topic, difficulty, title, narrative, instructions, starting_code,
test_type, function_name, input_variable, output_variable,
expected_variables, applies_stats, validation_tests, hints, reward

# models/challenge.py — ChallengeReward fields, exactly:
xp, gold, title, achievement

# content.py
ContentStore(sources: Dict[str, Tuple[dir, suffixes, loader]])
ContentStore.refresh() -> bool
```

`test_type` is exactly one of `"function" | "script_variable" | "variables" | "script_output"` (`models/challenge.py:25`). There is no fifth type.

### Anti-patterns to guard against

1. **Do not write a second parser.** Extend `story_loader.py`. A new module that re-tokenizes `.txt` duplicates 200 working lines and drifts from the `.scene` grammar.
2. **Do not use an LLM to "analyze" the story file.** The ask is a *predefined format*. Parsing is deterministic; an LLM adds latency, cost, and nondeterministic content on every hot-reload.
3. **Do not break `.scene`.** 18 chapters and 24 challenge JSONs ship today. Both authoring paths must keep working — this is additive.
4. **Do not invent `ChallengeDefinition` fields.** `difficulty` is a free string but the UI reads `tutorial | easy | medium | hard | boss`.
5. **Do not change `sandbox._call` semantics.** A list input spreads as positional args. The format must express this, not fight it.
6. **Do not put content in the parser.** `story_loader.py`'s docstring states: *"It never contains story content itself."*

---

## Phase 1 — Freeze the format (no code)

**What to implement:** `docs/12_txt_authoring.md` (the authoring contract) plus one worked example `story/example_merchant.txt` that Phase 2 will parse.

**The format.** One new top-level block, `@challenge`, sibling to `@scene`. Every construct inside it copies a construct that already parses:

```
@scene marketplace

background: market.png

dialogue:
"The merchant blocks your path."

npc Merchant:
"Sort my takings, traveler, and the road is yours."

mission: merchant_ledger

reward:
xp: 100
gold: 50

next: crossroads


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

**Grammar rules — every one reuses an existing convention:**

| Line | Maps to | Copies the convention at |
|---|---|---|
| `@challenge <id>` | `challenge_id` | `@scene` split, `story_loader.py:22` |
| `topic:` `difficulty:` `title:` | same-named fields | `background:` scalar, `story_loader.py:61` |
| `narrative:` + quoted lines | `narrative` (joined `\n`) | `dialogue:`, `story_loader.py:104` |
| `instructions:` + quoted lines | `instructions` (joined `\n`) | `dialogue:`, `story_loader.py:104` |
| `hints:` + quoted lines | `hints` (list) | `dialogue:`, `story_loader.py:104` |
| `code:` + raw lines | `starting_code` | **new** — verbatim, not quoted |
| `tests:` + `in -> out` lines | `validation_tests` | `choice:` arrow form, `story_loader.py:147` |
| `variables:` + `name: type` | `expected_variables` | `reward:` key-value block, `story_loader.py:162` |
| `reward:` block | `reward` | `reward:`, `story_loader.py:162` verbatim |

**The `test:` line** collapses four JSON fields into one:

| Written | `test_type` | Other fields set |
|---|---|---|
| `test: function sort_takings` | `function` | `function_name="sort_takings"` |
| `test: variables` | `variables` | reads the `variables:` block |
| `test: variables stats` | `variables` | + `applies_stats=True` |
| `test: script in=nums out=total` | `script_variable` | `input_variable`, `output_variable` |
| `test: output in=name` | `script_output` | `input_variable` |

**The `tests:` line** is `<json> -> <json>`, both sides `json.loads`-ed into `{"input": left, "expected": right}` — the exact shape `challenges/dragon_trial.json` already uses.

> **The double-bracket rule.** `sandbox._call` spreads a list input as positional args. A function taking *one list* needs `[[3,1,2]] -> ...`; a function taking *three numbers* uses `[3,1,2] -> ...`. This mirrors today's JSON exactly — it is not new behavior. Phase 4 adds a validator warning for the common mistake.

**Verification checklist:**
- [ ] `docs/12_txt_authoring.md` exists and documents every row above
- [ ] `story/example_merchant.txt` exists, valid per spec, **not** wired into the spine yet
- [ ] Every field named in the doc appears in `models/challenge.py` — grep each
- [ ] `docs/03_story_language.md` gains a link to the new doc

**Anti-pattern guards:**
- No field in the doc that `ChallengeDefinition` does not define
- No new `test_type` value beyond the four in `models/challenge.py:25`

---

## Phase 2 — Parse `@challenge` in `story_loader.py`

**What to implement:** copy the block-parsing shape of `_parse_block` (`story_loader.py:38-228`) into a new `_parse_challenge_block`, and split the file on both `@scene` and `@challenge`.

Read `story_loader.py:38-228` first and copy its idioms:
- the `while i < len(lines)` cursor with explicit `continue` after inner loops — `story_loader.py:88-102` (the `npc` block) is the model for every quoted-line section
- the `line.split(":", 1)[1].strip()` scalar form — `story_loader.py:61-66`
- the `reward:` key-value loop — `story_loader.py:162-185`, reusable verbatim for the challenge reward

**Signature changes (keep the old ones alive):**

```python
def parse_scene_file(filepath) -> List[ParsedScene]:                      # UNCHANGED
def parse_content_file(filepath) -> Tuple[List[ParsedScene], List[ChallengeDefinition]]:   # new
def load_all_scenes(story_dir) -> Dict[str, ParsedScene]:                 # UNCHANGED
def load_inline_challenges(story_dir) -> Dict[str, ChallengeDefinition]:  # new
```

`parse_scene_file` becomes the compat shim (`return parse_content_file(fp)[0]`) because `story_loader.py:241` and `story_loader.py:264` call it today.

**`code:` block termination** — the only genuinely new parsing rule. Collect lines verbatim until a line that is at column 0 *and* matches a known section keyword (`topic|difficulty|title|test|narrative|instructions|code|tests|hints|variables|reward|@scene|@challenge`) followed by `:` or whitespace. Python starter code at column 0 (`def foo():`) collides with none of those.

```python
# ponytail: keyword-terminated raw block. Breaks only if starter code has a
# column-0 line literally named like a section tag. Switch to a fenced
# delimiter if that ever happens.
```

**Both suffixes, one parser.** `load_all_scenes` and `load_inline_challenges` both accept `.scene` and `.txt` — an author may use `@challenge` in a `.scene` file, or write pure narrative in a `.txt`. The extension carries no meaning.

**Verification checklist:**
- [ ] Extend `_selfcheck()` (`story_loader.py:247`) with a `@challenge` case asserting: `test: function f` → `test_type == "function"` and `function_name == "f"`; `tests:` → `[{"input": …, "expected": …}]`; `code:` preserves indentation exactly
- [ ] `python -m app.engine.story_loader` passes (run from `backend/`)
- [ ] `load_all_scenes(story_dir)` still returns all 18 existing scenes — assert the count
- [ ] `story/example_merchant.txt` parses to 1 scene + 1 challenge

**Anti-pattern guards:**
- Do not modify `_parse_block` — `@scene` behavior must stay byte-identical
- Do not add story or challenge prose to the parser module
- `parse_scene_file` must keep returning `List[ParsedScene]`, not a tuple

---

## Phase 3 — Wire it into the server

**What to implement:** three edits in `backend/app/main.py`, all inside `main.py:72-90`.

```python
# main.py:72-74 — merge the two challenge sources
SCENES = load_all_scenes(STORY_DIR)
CHALLENGES = {**load_all_challenges(CHALLENGES_DIR), **load_inline_challenges(STORY_DIR)}
INTERACTIONS = load_all_interactions(INTERACTIONS_DIR)
```

Inline challenges win on an id collision — the file you are editing is the one you meant. Log a warning on collision, copying the wording at `challenge_loader.py:59-63`.

```python
# main.py:76-80 — teach the hot-reload about .txt
_CONTENT = ContentStore({
    "scenes":       (STORY_DIR, (".scene", ".txt"), load_all_scenes),
    "challenges":   (CHALLENGES_DIR, (".json",), load_all_challenges),
    "inline":       (STORY_DIR, (".scene", ".txt"), load_inline_challenges),
    "interactions": (INTERACTIONS_DIR, (".json",), load_all_interactions),
})
```

`refresh_content()` (`main.py:83-90`) then merges `data["challenges"]` with `data["inline"]` the same way, and its print line gains the inline count.

> `content.py`'s `demo()` asserts a `.txt` file is *ignored* by a `.scene`-suffixed store. That assertion is about suffix filtering in general and still holds for that store — do not delete it.

**Verification checklist:**
- [ ] `GET /` reports `challenges_loaded` including `merchant_ledger`
- [ ] `GET /api/scene/marketplace` returns the scene with its challenge inlined (route reads `CHALLENGES[cid]` at `main.py:239`)
- [ ] Edit `story/example_merchant.txt`, hit any endpoint, confirm `[content] reloaded` prints without a server restart
- [ ] `python -m app.engine.content` still passes

**Anti-pattern guards:**
- Do not point `ContentStore` at `STORY_DIR` with a loader returning scenes under the `"challenges"` key — the merge belongs in `refresh_content`, not the store
- Do not drop the existing `challenges/*.json` source

---

## Phase 4 — Validate and document

**What to implement:** run inline challenges through the existing validator, and add the one new authoring trap.

`validate_challenges()` (`challenge_loader.py:69`) already catches missing `output_variable`, starter code shadowing the injected input, missing `function_name`, missing `expected_variables`, unknown `test_type`, and empty `validation_tests`. Inline challenges inherit all of it free once Phase 3 merges them, because `main.py:102` validates the merged dict.

Add one check:

```
{cid}: function takes 1 parameter but every test passes a bare list —
these spread as positional args. Wrap as [[...]] if the function takes one list.
```

Detect by counting parameters in `starting_code`'s `def <function_name>(...)` and comparing against `isinstance(t["input"], list)` across `validation_tests`.

**Docs to update:**
- `docs/03_story_language.md` — add `@challenge` to the tag list (currently lists `@scene` only)
- `docs/04_challenge_system.md` — note a challenge may live inline in a story file; JSON remains supported
- `docs/01_project_overview.md` — "…write new `.scene` files and challenge JSONs" becomes "…a single story file"
- `README.md` — one line in the authoring section

**Verification checklist:**
- [ ] Deliberately author a bad inline challenge (1-param function, tests passing bare lists); confirm the warning prints at startup
- [ ] Remove it; confirm a clean startup has zero `[challenge warning]` lines
- [ ] Every doc above mentions `@challenge`

---

## Phase 5 — Final verification

Run in order from `backend/`:

```bash
python -m app.engine.story_loader     # parser self-check incl. @challenge
python -m app.engine.content          # hot-reload self-check
python test_content.py                # content integrity + spine walk
```

**`test_content.py` will fail Phase 1's example on purpose** — it flags `orphan challenge never played` for any challenge no scene references, and `example_merchant`'s scene is not on the spine. Pick one:
- (a) wire `example_merchant` into the spine as a real optional chapter, or
- (b) keep it a fixture and teach `test_content.py` to skip files prefixed `example_`

**(b) is the lazy choice** — an example that must stay playable will rot.

**Grep checks for invented APIs:**
```bash
grep -rn "test_type" backend/app/engine/story_loader.py   # only the 4 real values
grep -rn "ChallengeDefinition(" backend/app/engine/       # every field must exist
```

**Acceptance — the point of the whole plan:**
- [ ] A single new `.txt` file in `story/`, referenced by `next:` from an existing chapter, produces a fully playable scenario with a working, graded coding problem
- [ ] Zero files touched outside `story/`
- [ ] Zero server restarts
- [ ] All 18 existing `.scene` chapters and 24 challenge JSONs still pass `test_content.py`

---

## Out of scope (deliberately)

| Not doing | Why | Add when |
|---|---|---|
| LLM analysis of freeform prose | The ask is a predefined format; parsing is deterministic and free | An author wants to paste unstructured prose and have it auto-structured |
| Inline `@interaction` blocks | Widgets are config-shaped, not prose-shaped; JSON fits better | Interaction authoring becomes the bottleneck |
| A web-based scenario editor | The format is editable in Notepad | Non-technical authors join |
| Migrating the 24 existing JSONs | They work; churn for no gain | A challenge needs editing anyway |
