# PyMaze

**Learn Python by playing an RPG where code is your weapon.**

PyMaze is a scenario-driven Python learning engine. Instead of textbook exercises, learners write real Python to solve in-world problems — initialising a character's stats with variables, surviving a dragon's trial with an algorithm, teaching a gate to choose with `if`/`elif`/`else`.

It is built as an **engine, not a game**. The engine is permanent; every scene, challenge, interaction and asset is loaded from external data files. Adding `story/chapter_18.scene` requires zero engine changes.

### 🔥 Recent Upgrades
- **Multi-User Authentication**: Full Login/Registration system using JWT tokens to secure your journey.
- **MongoDB Atlas Integration**: Progress is safely persisted to the cloud instead of local memory.
- **Player Profile & Heatmap**: Track your daily puzzle-solving streaks with a 90-day GitHub-style activity heatmap!
- **Fast-Forward**: A new "Skip Scene" feature to instantly jump to the next interactive challenge or system popup.
- **Robust Error Handling**: Graceful UI fallbacks for backend disconnections or database timeouts.

---

## Quick start

**Requirements:** Python 3.11+, Node.js 20+, and (optionally) a MongoDB Atlas cluster.

```bash
# 1. Backend  (terminal 1)
cd backend
python -m venv venv
venv/Scripts/activate         # Windows;  source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env          # then set JWT_SECRET_KEY — the app refuses to start without it
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
PyMaze/
├── backend/app/
│   ├── main.py              FastAPI routes
│   ├── auth.py              password hashing + JWT
│   ├── db.py                MongoDB, or a local JSON store when unconfigured
│   ├── engine/              story_loader · challenge_loader · interaction_loader
│   │                        executor · sandbox · scoring · templating
│   │                        player_manager · save_system · content
│   └── models/              Pydantic models (player, user, scene, challenge, interaction)
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
└── docs/                    engine documentation
```

**Content and engine are strictly separated.** Nothing under `story/`, `challenges/`, `interactions/` or `assets/` requires a code change to add.

---

## Configuration

| Variable | Side | Default | Purpose |
|---|---|---|---|
| `JWT_SECRET_KEY` | backend | **none — required** | Signs session tokens. Startup fails without it, because a shared default would let anyone mint a token for any account. |
| `MONGODB_URI` | backend | *(empty)* | Where users and saves live. Empty runs off a local JSON file under `backend/saves/` — single machine only. |
| `MONGODB_DB` | backend | `pymaze` | Database name within the cluster. |
| `JWT_ALGORITHM` | backend | `HS256` | Token signing algorithm. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | backend | `1440` | Session lifetime. |
| `PYMAZE_CORS_ORIGINS` | backend | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated origins allowed to call the API. |
| `VITE_API_BASE` | frontend | `http://localhost:8000` | Backend origin. Inlined at **build** time, not runtime. |

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env` to set these locally. Generate a key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Deployment

The two halves deploy independently.

**Backend** — any host that runs a Python ASGI app (Railway, Render, Fly.io, a VM):

```bash
pip install -r backend/requirements.txt
cd backend
MONGODB_URI="mongodb+srv://..." \
JWT_SECRET_KEY="<32 random bytes, hex>" \
PYMAZE_CORS_ORIGINS="https://your-frontend.example.com" \
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The app pings the database and creates its indexes at startup, so a bad URI or
an Atlas IP allowlist that doesn't include the host fails immediately with the
reason, rather than at the first login.

The working directory must be `backend/`, and `story/`, `challenges/`, `interactions/`, `assets/` and `config/` must be present one level up — the engine resolves them relative to the repo root and serves `assets/` straight off disk.

**Frontend** — any static host (Vercel, Netlify, Cloudflare Pages, GitHub Pages):

```bash
cd frontend
VITE_API_BASE="https://your-backend.example.com" npm run build
# deploy frontend/dist/
```

### Before going public

One thing is still a local default, not production behaviour:

- **Code execution is sandboxed by restricted globals**, which stops accidents, not a determined attacker. Untrusted public traffic wants an OS-level sandbox (container, gVisor, or a dedicated runner) and a wall-clock timeout.

This is fine for local use, a demo, or a trusted classroom. (Note: The previous limitation of single-player local saves has been resolved with our new MongoDB and JWT Auth architecture!)

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
| `POST`| `/api/auth/register` | Register a new user account |
| `POST`| `/api/auth/login` | Authenticate and receive a JWT access token |
| `GET` | `/api/scene/{scene_id}` | A parsed scene with its challenges and interactions, rendered for the live player |
| `GET` | `/api/player` | Current player state (Requires Auth) |
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
