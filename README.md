# PyBe

**Learn Python by playing an RPG where code is your weapon.**

PyBe is a scenario-driven Python learning engine. Instead of textbook exercises, learners write real Python to solve in-world problems — initialising a character's stats with variables, surviving a dragon's trial with an algorithm, teaching a gate to choose with `if`/`elif`/`else`.

It is built as an **engine, not a game**. The engine is permanent; every scene, challenge, interaction and asset is loaded from external data files. Adding `story/chapter_18.scene` requires zero engine changes.

---

## Quick start

**Requirements:** Python 3.11+ and Node.js 20+.

```bash
# 1. Backend  (terminal 1)
cd backend
python -m venv venv
venv/Scripts/activate         # Windows;  source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

Open the Vite URL it prints (default <http://localhost:5173>). The backend must be running first — the frontend fetches all content from it.

Startup prints any authoring problems it finds (missing backgrounds, unknown widgets, malformed challenges) so a broken chapter fails loudly instead of showing a black screen.

---

## Project layout

```
PyBe/
├── backend/app/
│   ├── main.py              FastAPI routes
│   ├── engine/              story_loader · challenge_loader · interaction_loader
│   │                        executor · sandbox · scoring · templating
│   │                        player_manager · save_system · content
│   └── models/              Pydantic models (player, scene, challenge, interaction)
├── frontend/src/
│   ├── App.jsx              Root shell (HUD + SceneManager)
│   ├── config.js            Backend origin (VITE_API_BASE)
│   ├── index.css            Design system
│   └── components/          DialogueBox · ChallengePanel · HUD · SystemPanel
│                            SceneBackground · overlays · interactions/
├── story/                   *.scene   — narrative, in the custom DSL
├── challenges/              *.json    — coding missions
├── interactions/            *.json    — interactive beats
├── assets/                  backgrounds · characters · music · sound · animations
├── config/                  widgets.json and other tunables
├── saves/                   runtime player saves (gitignored)
└── docs/                    engine documentation
```

**Content and engine are strictly separated.** Nothing under `story/`, `challenges/`, `interactions/` or `assets/` requires a code change to add.

---

## Configuration

| Variable | Side | Default | Purpose |
|---|---|---|---|
| `PYBE_CORS_ORIGINS` | backend | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated origins allowed to call the API. |
| `VITE_API_BASE` | frontend | `http://localhost:8000` | Backend origin. Inlined at **build** time, not runtime. |

Copy `frontend/.env.example` to `frontend/.env` to override locally.

---

## Deployment

The two halves deploy independently.

**Backend** — any host that runs a Python ASGI app (Railway, Render, Fly.io, a VM):

```bash
pip install -r backend/requirements.txt
cd backend
PYBE_CORS_ORIGINS="https://your-frontend.example.com" \
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The working directory must be `backend/`, and `story/`, `challenges/`, `interactions/`, `assets/` and `config/` must be present one level up — the engine resolves them relative to the repo root and serves `assets/` straight off disk.

**Frontend** — any static host (Vercel, Netlify, Cloudflare Pages, GitHub Pages):

```bash
cd frontend
VITE_API_BASE="https://your-backend.example.com" npm run build
# deploy frontend/dist/
```

### Before going public

Two things are single-player local defaults, not production behaviour:

- **Saves are a single shared player.** `player_manager` holds one in-memory player and `saves/` writes flat JSON. Multi-user deployment needs sessions and a real datastore.
- **Code execution is sandboxed by restricted globals**, which stops accidents, not a determined attacker. Untrusted public traffic wants an OS-level sandbox (container, gVisor, or a dedicated runner) and a wall-clock timeout.

Both are fine for local use, a demo, or a trusted classroom.

---

## Authoring content

Write a scene, drop in assets, define challenges, restart. Nothing else.

```
@scene chapter_3_the_market
background: market.png
music: bustle.mp3

npc Merchant:
  "You'll need a list to carry all that, traveler."

mission: lists_intro
next: chapter_4_road_north
```

| Tag | Purpose |
|---|---|
| `@scene [id]` | Declares a scene and its identifier |
| `background:` / `music:` | Scene media, by filename |
| `npc [Name]:` | NPC dialogue block |
| `dialogue:` | Narration |
| `choice:` | Branching player choices |
| `mission: [id]` | Triggers a coding challenge from `challenges/` |
| `interactive: [id]` | Plays an interactive beat from `interactions/` |
| `system: [variant]` | Renders a System UI panel |
| `reward:` / `achievement:` | Grants XP, gold, titles, badges |
| `condition:` | State-based branching |
| `next: [id]` | The following scene |

While the dev server runs, edits to `story/`, `challenges/` and `interactions/` are picked up automatically — `uvicorn --reload` only watches `.py`, so the engine re-reads content files itself.

Full detail: [`docs/03_story_language.md`](docs/03_story_language.md) and [`docs/04_challenge_system.md`](docs/04_challenge_system.md).

---

## API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check; lists loaded scenes, challenges, interactions |
| `GET` | `/api/scene/{scene_id}` | A parsed scene with its challenges and interactions, rendered for the live player |
| `GET` | `/api/player` | Current player state |
| `POST` | `/api/execute` | Run learner code against a challenge's validation rules |
| `POST` | `/api/interaction/complete` | Grant an interaction reward (idempotent) |
| `POST` | `/api/advance` | Advance to the next scene, evaluating conditions |
| `POST` | `/api/save` | Save the game |
| `GET` | `/api/load` | Load the most recent save |

Interactive API docs are at `/docs` while the server runs.

---

## Documentation

| Document | Covers |
|---|---|
| [`prd.md`](prd.md) | Product requirements — vision, systems, scope |
| [`docs/01_project_overview.md`](docs/01_project_overview.md) | Orientation |
| [`docs/02_engine_architecture.md`](docs/02_engine_architecture.md) | Engine internals |
| [`docs/03_story_language.md`](docs/03_story_language.md) | `.scene` DSL reference |
| [`docs/04_challenge_system.md`](docs/04_challenge_system.md) | Challenge schema and executor |
| [`docs/05_rpg_system.md`](docs/05_rpg_system.md) | Stats, scoring, progression |
| [`docs/06_asset_pipeline.md`](docs/06_asset_pipeline.md) | Asset conventions |
| [`docs/07_ui_guidelines.md`](docs/07_ui_guidelines.md) | Design system |
| [`docs/08_story_bible.md`](docs/08_story_bible.md) | Characters, world, tone |
| [`docs/09_interaction_system.md`](docs/09_interaction_system.md) | Interactive beats and the widget registry |
| [`docs/10_background_art.md`](docs/10_background_art.md) | Scene art direction |
| [`docs/11_system_panels.md`](docs/11_system_panels.md) | The System's nine panel variants |
| [`LLM_RULEBOOK.md`](LLM_RULEBOOK.md) | Rules for AI contributors |

---

## Contributing

The engine has eight standing rules, and they are the whole architecture:

1. Never hardcode story text — narrative lives in `.scene` files.
2. Don't modify existing engine APIs unless truly necessary.
3. Keep the engine modular and data-driven.
4. Add features as modules, not additions to core files.
5. Treat `.scene` files as the single source of truth.
6. Preserve backward compatibility — Chapter 0 must always run.
7. Prefer configuration over hardcoded constants.
8. Document new modules in `docs/`.

## Current content

Chapter 0 (The Awakening) → Chapter 1 (The Dragon's Trial) → Chapter 1b (Wisdom of the System) → Chapter 2 (Trial of Choice). Every path through the Dragon's judgment converges — failure costs stats, never progress.
