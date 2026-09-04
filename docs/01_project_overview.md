# Project Overview

## Vision
**PyMaze** is a modular, scenario-driven Python learning engine. It is designed not as a hardcoded game, but as an extensible engine where all content is data-driven. The core vision is to abandon dry, textbook-style learning in favor of relatable, engaging, and high-stakes scenarios (ranging from fantasy RPG to slice-of-life comedy).

## Goals
- Provide an interactive, narrative-driven learning experience.
- Maintain a permanent, robust engine while allowing all story and coding content to be infinitely replaceable and expandable.
- Keep the system entirely data-driven (external files for stories, assets, challenges).
- The author should only need to write new story files and add assets to expand the game, without ever touching the engine code. A scenario and its coding problem can live in a single file — an `@challenge` block sits beside the `@scene` that triggers it (see [12_txt_authoring.md](12_txt_authoring.md)) — or the problem can stay in its own `challenges/*.json`, which is still fully supported.

## Learning Philosophy
- **Practical Application:** Users learn Python by solving everyday or epic problems using code.
- **Progressive Difficulty:** Start with basic variables and datatypes, moving through control flow (if/elif/else), loops, collections, functions, and advanced concepts like Exception Handling and File I/O.
- **Fail Gracefully:** Mistakes in code (like infinite loops or syntax errors) are part of the game and should result in informative feedback (or temporary in-game stat drains), but should never permanently discourage the learner.
- **Immediate Feedback:** Fast, deterministic code execution ensures learners instantly know if their logic is sound.
