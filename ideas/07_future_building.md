# Future Building — What to Build, Roughly in Order

Separates **content** (authorable in `.scene` + `.json`, no engine change) from
**engine work** (needs code). The whole architecture is designed so content
scales without engine changes — so most of the roadmap is content, and the engine
list is deliberately short.

## Content track (no engine changes — just author files)

This is the bulk of the work and any content author can do it. Priority order
follows the curriculum ([01_curriculum_map.md](01_curriculum_map.md)).

| Priority | Deliverable | Files |
|---|---|---|
| P0 | Finish **2b Operators** (a challenge exists; wrap it in a B-chapter) | `story/chapter_2b_*.scene`, `interactions/op_*.json` |
| P0 | **3 + 3b Loops** (a challenge exists; build the Echoing Halls) | `story/`, `challenges/`, `interactions/` |
| P1 | **4 + 4b Lists** | as above |
| P1 | **5 + 5b Dicts/Tuples/Sets** | as above |
| P2 | **6 + 6b Strings** | as above |
| P2 | **7/7b/7c Functions + Scope** | as above |
| P3 | **8 + 8b Exceptions** (the thematic hinge — do it well) | as above |
| P3 | **9 + 9b File I/O** | as above |
| P4 | **10 + 10b Comprehensions** | as above |
| P4 | **11 + 11b OOP** (capstone) | as above |
| P5 | **12 Boss: The Unhandled** (DSA + OOP) | as above |

Each row is: 1 A-chapter scene, 1–2 B-chapter scenes, ~6–10 interaction JSONs,
2–3 challenge JSONs, plus backgrounds. All within the existing schema.

## Engine track (needs code — keep this list short on purpose)

Only build what content genuinely can't express. In rough priority:

1. **Execution timeout in the sandbox.** *(highest value, needed anyway.)* The
   infinite-loop VIT penalty and the whole loops chapter assume runaway code is
   caught. Today an infinite loop from a learner hangs the request. A wall-clock
   timeout (subprocess or thread with a hard kill) is the one real correctness
   gap. Also the prerequisite for any public deployment
   (noted in [README](../README.md#before-going-public)).
2. **New interaction widgets**, curriculum-ordered
   ([05_mechanics.md](05_mechanics.md#widget-proposals)). Each is a self-contained
   React component + registry entry — the cheap kind of engine work. Build a
   widget only when a `predict_output`/`sort_types`/`build_statement` JSON can't
   already express the beat.
3. **"Solution shape" scoring hooks.** To grant mastery achievements
   ([06_achievements.md](06_achievements.md)) — detect "used a comprehension",
   "used a `set`", "named things well". The scoring engine already inspects code;
   this extends it. Config-driven per challenge (e.g. `reward_if: {uses: "set"}`).
4. **Per-virtue reward feedback.** RewardPopup shows *which* stat rose and *why*
   ("+3 WIS — good names"). Small frontend + a reason string from scoring.
5. **Battle mode.** Timed code-snippet combat (RPG doc). Bigger; schedule after
   the core curriculum exists, so battles reinforce concepts already taught.
6. **Multi-user + real saves.** Sessions and a datastore, replacing the single
   in-memory player. A deployment feature, not a learning feature — do it when
   there are real users, not before ([README](../README.md#before-going-public)).

## Authoring pipeline improvements (nice-to-have)

The engine already validates challenges/interactions and warns on missing
backgrounds/widgets at startup — good. Cheap additions that would help content
velocity (the PRD's "<1 day per chapter" goal):

- **A `.scene` linter** that flags a B-chapter with too-low interaction density
  (three `dialogue:` blocks with no action between) — enforces the quality bar
  from [04_b_chapters.md](04_b_chapters.md#interaction-budget--the-quality-bar).
- **A "story graph" dump** — an endpoint or script that walks `next:`/`condition:`
  across all scenes and renders the branch map (like the ASCII graph in the PRD),
  so authors can see dead ends and unreachable scenes.
- **A challenge preview harness** — run a challenge's `validation_tests` against a
  known-good solution from the CLI, so authors verify a challenge before wiring
  it into a scene.

## Sequencing recommendation

1. **Ship the execution timeout first** — it unblocks loops, the infinite-loop
   curse, *and* deployment in one move.
2. **Then run the content track P0→P2 purely in data** — operators through
   functions need no new widgets if you lean on `predict_output`/`build_statement`;
   this proves the "author a chapter in a day" claim and gets the from-scratch
   path to "functions" (a genuinely useful stopping point) fast.
3. **Add widgets lazily**, only where a JSON beat can't carry the idea (slicing,
   loop-stepping, and OOP forging are the three that probably truly need one).
4. **Exceptions chapter is the milestone to aim for** — it's where teaching and
   story fuse (the Blight *is* the lesson). Treat it as the Act III centerpiece
   and give it the polish 1b got.

## The north star

The braid ([README](README.md#the-one-idea-everything-else-hangs-on-the-ab-braid))
plus the metaphor spine plus the existing data-driven engine means **the game can
grow to a full from-scratch Python course without a single architectural rewrite.**
Every item above is either a `.scene`/`.json` file or a small, isolated module.
That's the design working as intended — keep it that way.
