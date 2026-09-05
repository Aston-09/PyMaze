# Challenge System

The Challenge System handles the evaluation of user-written Python code. Story files (`.scene`) reference challenge IDs, and the engine loads the logic from `challenges/*.json`.

A challenge may also be authored **inline in the story file itself**, as an `@challenge` block beside the `@scene` that triggers it — see [12_txt_authoring.md](12_txt_authoring.md). Both routes produce the same `ChallengeDefinition` and everything below applies unchanged; `challenges/*.json` remains fully supported. On an id collision the inline block wins.

## Challenge Configuration (`.json`)
Each challenge defines:
- **Topic & Difficulty**
- **Description & Instructions**
- **Required Concepts** (e.g., must use a `for` loop)
- **Validation Rules** (Test cases: inputs and expected outputs)
- **Execution Type** (`function` vs `script_variable`)
- **Rewards**

## Evaluators

### Python Evaluator
Safely runs user-submitted Python code in an isolated environment (e.g., restricted `exec` globals).
- **Function Testing:** The engine injects input data into a user-defined function and asserts the return value matches expected outputs.
- **Script Variable Testing:** The engine populates variables in the global scope behind the scenes, runs the user's raw script (like an if/else block), and asserts that a specific output variable was set correctly by the user. `input_variable` may name several variables, comma-separated, in which case each test case's `input` is a list bound to them positionally.

> **Which type, and when.** Functions are not taught until chapter 7b, so no
> mission before it may use `function` — a beginner should never meet `def` as
> incidental scaffolding around the thing they are actually learning. Use
> `script_variable` (with as many input names as the problem needs) up to that
> point. `backend/test_solutions.py` enforces this and plays a model answer
> through every one of those missions.

### DSA Evaluator
For algorithmic challenges (e.g., "Longest Substring Without Repeating Characters"), the evaluator checks standard input/output sets and enforces time/space complexity limits where applicable.

## Scoring Rules
The Scoring Engine evaluates multiple dimensions of the user's code to grant specific rewards:
- **Experience (XP) ⭐**: Base progression for completing challenges, defeating bosses, etc.
- **Intelligence (INT) 🧠**: Awarded for correct syntax, logic, and proper use of collections or functions.
- **Wisdom (WIS) 📚**: Awarded for clean, readable code with meaningful variable names (e.g., `player_hp = 100` instead of `a = 100`).
- **Dexterity (DEX) ⚡**: Awarded for coding efficiency (fewer unnecessary lines, list comprehensions over bulky loops).
- **Vitality (VIT) ❤️**: Persistence. Lost slightly for infinite loops or syntax crashes; gained for completing hard quests.
- **Mana (MP) 🔷**: Coding energy. Every submission costs Mana. Correct solutions refund it. Repeated guessing drains it, encouraging thinking before submitting.
