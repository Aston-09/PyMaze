"""
PyMaze Backend API

Data-driven API that loads all content from external .scene and .json files.
"""
import os
import re
import json
from contextlib import asynccontextmanager
from functools import lru_cache
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Literal

from app.engine.story_loader import (
    CONTENT_SUFFIXES, load_all_scenes, load_inline_challenges,
)
from app.engine.challenge_loader import load_all_challenges, validate_challenges
from app.engine.interaction_loader import load_all_interactions, validate_interactions
from app.engine.content import ContentStore
from app.engine.executor import execute_and_test
from app.engine.scoring import score_code
from app.engine.templating import render_for
from app.engine import player_manager
from app.engine.save_system import save_game, load_game
from app.models.player import PlayerState
from app.routers import auth
from app.auth import get_current_user
from app import db

# --- App Setup ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Fail at boot on a store that doesn't work, not at the first login."""
    print(f"[db] connected: {await db.connect()}")
    yield


app = FastAPI(title="PyMaze Engine API", lifespan=lifespan)

# Where the browser app is served from. Deployments set PYMAZE_CORS_ORIGINS to
# their own origin; the default covers `npm run dev`.
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "PYMAZE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True, # Need this for Authorization header if configured
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

# --- Load Content at Startup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
STORY_DIR = os.path.join(BASE_DIR, "story")
CHALLENGES_DIR = os.path.join(BASE_DIR, "challenges")
INTERACTIONS_DIR = os.path.join(BASE_DIR, "interactions")

CONFIG_DIR = os.path.join(BASE_DIR, "config")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")


def _merge_challenges(from_json: Dict, inline: Dict) -> Dict:
    """challenges/*.json plus the @challenge blocks authored in story files.

    Inline wins a collision — the file being edited is the one the author meant.
    Startup and hot-reload both go through here so they cannot drift apart.
    """
    for cid in sorted(from_json.keys() & inline.keys()):
        print(f"[content warning] Duplicate challenge_id '{cid}' inline in story/ — "
              f"overriding the one from challenges/.")
    return {**from_json, **inline}


SCENES = load_all_scenes(STORY_DIR)
CHALLENGES = _merge_challenges(
    load_all_challenges(CHALLENGES_DIR), load_inline_challenges(STORY_DIR)
)
INTERACTIONS = load_all_interactions(INTERACTIONS_DIR)

_CONTENT = ContentStore({
    "scenes": (STORY_DIR, CONTENT_SUFFIXES, load_all_scenes),
    "challenges": (CHALLENGES_DIR, (".json",), load_all_challenges),
    "inline": (STORY_DIR, CONTENT_SUFFIXES, load_inline_challenges),
    "interactions": (INTERACTIONS_DIR, (".json",), load_all_interactions),
})


def refresh_content() -> None:
    global SCENES, CHALLENGES, INTERACTIONS
    if _CONTENT.refresh():
        SCENES = _CONTENT.data["scenes"]
        CHALLENGES = _merge_challenges(_CONTENT.data["challenges"], _CONTENT.data["inline"])
        INTERACTIONS = _CONTENT.data["interactions"]
        print(f"[content] reloaded — {len(SCENES)} scenes, "
              f"{len(CHALLENGES)} challenges ({len(_CONTENT.data['inline'])} inline), "
              f"{len(INTERACTIONS)} interactions")


def _registered_widgets() -> List[str]:
    try:
        with open(os.path.join(CONFIG_DIR, "widgets.json"), encoding="utf-8") as f:
            return json.load(f).get("widgets", [])
    except (OSError, json.JSONDecodeError):
        return []

for _problem in validate_interactions(INTERACTIONS, _registered_widgets()):
    print(f"[interaction warning] {_problem}")
for _problem in validate_challenges(CHALLENGES):
    print(f"[challenge warning] {_problem}")

if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
else:
    print(f"[asset warning] assets directory not found: {ASSETS_DIR}")


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _frame_files(folder: str) -> List[str]:
    """The frame_N images in one art folder, in playing order.

    Sorted on the number rather than the name, so frame_10 follows frame_9
    instead of frame_1.
    """
    names = [
        n for n in os.listdir(folder)
        if os.path.splitext(n)[1].lower() in IMAGE_EXTS
    ]
    def order(name: str):
        match = re.search(r"(\d+)", os.path.splitext(name)[0])
        return (int(match.group(1)) if match else 0, name)
    return sorted(names, key=order)


@lru_cache(maxsize=1)
def _art_frame_map() -> Dict[str, List[str]]:
    """{stem: [paths under /assets]} for every folder of animation frames.

    A `background:` tag in a .scene file names a stem — a location
    ("ancient_library") or a character ("warden") — and the frontend animates
    whichever it finds here, with no per-character code. The player's own
    sprites live one level deeper, split by gender, and are keyed
    "player_male"/"player_female" for the request-time pick in
    `/api/backgrounds/frames`.
    """
    frames: Dict[str, List[str]] = {}
    for group in ("backgrounds", "characters"):
        root = os.path.join(ASSETS_DIR, group)
        if not os.path.isdir(root):
            continue
        for stem in sorted(os.listdir(root)):
            folder = os.path.join(root, stem)
            if not os.path.isdir(folder):
                continue
            if files := _frame_files(folder):
                frames[stem] = [f"{group}/{stem}/{n}" for n in files]
                continue
            # No images directly inside → a folder of variants (player/male, ...).
            for variant in sorted(os.listdir(folder)):
                sub = os.path.join(folder, variant)
                if os.path.isdir(sub) and (files := _frame_files(sub)):
                    frames[f"{stem}_{variant}"] = [
                        f"{group}/{stem}/{variant}/{n}" for n in files
                    ]
    return frames


def _missing_backgrounds() -> List[str]:
    """Backgrounds a scene asks for that aren't on disk.

    A missing file is a silent black screen at runtime, so it is worth one
    line at startup.
    """
    bg_dir = os.path.join(ASSETS_DIR, "backgrounds")
    frame_map = _art_frame_map()
    missing = []
    for scene in SCENES.values():
        wanted = {scene.background} | {b.ref for b in scene.beats if b.type == "background"}
        for name in wanted:
            if not name:
                continue
            stem = os.path.splitext(name)[0]
            if stem in frame_map or stem == "player":
                continue  # animated folder, or gender-resolved at request time
            if not os.path.isfile(os.path.join(bg_dir, name)):
                missing.append(f"{scene.scene_id}: background '{name}' not found")
    return missing

for _problem in _missing_backgrounds():
    print(f"[asset warning] {_problem}")

# --- Dependency ---
async def get_player_state(username: str = Depends(get_current_user)) -> PlayerState:
    player = await load_game(username)
    if not player:
        player = PlayerState()
        await save_game(player, username)
    return player

# --- Request/Response Models ---
class ExecuteRequest(BaseModel):
    code: str
    challenge_id: str

class AdvanceRequest(BaseModel):
    current_scene: str

class InteractionCompleteRequest(BaseModel):
    interaction_id: str

class AppearanceRequest(BaseModel):
    gender: Literal["male", "female"]


# --- Routes ---

@app.get("/")
async def root():
    return {
        "message": "PyMaze Engine API is running.",
        "story_dir": STORY_DIR,
        "scenes_loaded": list(SCENES.keys()),
        "challenges_loaded": list(CHALLENGES.keys()),
    }

@app.get("/api/scene/{scene_id}")
async def get_scene(scene_id: str, username: str = Depends(get_current_user), player: PlayerState = Depends(get_player_state)):
    refresh_content()
    if scene_id not in SCENES:
        raise HTTPException(status_code=404, detail=f"Scene '{scene_id}' not found")

    scene = SCENES[scene_id]
    response = render_for(scene.model_dump(), player)

    # Attach every definition the beat stream refers to.
    missions = [b.ref for b in scene.beats if b.type == "mission" and b.ref in CHALLENGES]
    interactions = [b.ref for b in scene.beats if b.type == "interactive" and b.ref in INTERACTIONS]

    response["challenges"] = {
        cid: render_for(CHALLENGES[cid].model_dump(), player) for cid in missions
    }
    response["interactions"] = {
        iid: render_for(INTERACTIONS[iid].model_dump(), player) for iid in interactions
    }
    if scene.mission and scene.mission in CHALLENGES:
        response["challenge"] = response["challenges"][scene.mission]

    return response

@app.post("/api/interaction/complete")
async def complete_interaction(request: InteractionCompleteRequest, username: str = Depends(get_current_user), player: PlayerState = Depends(get_player_state)):
    if request.interaction_id not in INTERACTIONS:
        raise HTTPException(status_code=404, detail="Interaction not found")

    interaction = INTERACTIONS[request.interaction_id]
    already_done = request.interaction_id in player.completed_missions

    if not already_done:
        if interaction.reward:
            player_manager.award_xp(player, interaction.reward.xp)
            player_manager.award_gold(player, interaction.reward.gold)
            if interaction.reward.achievement:
                player_manager.unlock_achievement(player, interaction.reward.achievement)
        player_manager.complete_mission(player, request.interaction_id)
        await save_game(player, username)

    return {
        "awarded": not already_done,
        "reward": interaction.reward.model_dump() if interaction.reward else None,
        "player": player.model_dump(),
    }

@app.get("/api/player")
async def get_player(username: str = Depends(get_current_user), player: PlayerState = Depends(get_player_state)):
    """Return the current player state."""
    return player.model_dump()


@app.post("/api/player/appearance")
async def set_appearance(request: AppearanceRequest, username: str = Depends(get_current_user), player: PlayerState = Depends(get_player_state)):
    """Pick which player sprite set this learner sees for the rest of the run."""
    player.gender = request.gender
    await save_game(player, username)
    return {"player": player.model_dump()}


@app.get("/api/backgrounds/frames")
async def background_frames(username: str = Depends(get_current_user), player: PlayerState = Depends(get_player_state)):
    """Every animated art folder, as {stem: [paths under /assets]}.

    "player" resolves here rather than in the .scene file, so a chapter can
    say `background: player` and each learner sees their own sprite.
    """
    frames = dict(_art_frame_map())
    chosen = frames.get(f"player_{player.gender or 'male'}")
    if chosen:
        frames["player"] = chosen
    return frames


@app.post("/api/execute")
async def execute_code(request: ExecuteRequest, username: str = Depends(get_current_user), player: PlayerState = Depends(get_player_state)):
    refresh_content()

    if request.challenge_id not in CHALLENGES:
        raise HTTPException(status_code=404, detail=f"Challenge not found")

    challenge = CHALLENGES[request.challenge_id]
    validation_tests = render_for(challenge.validation_tests, player)

    result = execute_and_test(
        user_code=request.code,
        test_type=challenge.test_type,
        validation_tests=validation_tests,
        function_name=challenge.function_name,
        input_variable=challenge.input_variable,
        output_variable=challenge.output_variable,
        expected_variables=challenge.expected_variables,
    )

    stat_bonuses = {"int_bonus": 0, "wis_bonus": 0, "dex_bonus": 0}
    judgment = None
    dragon_narrative = None

    if result.get("success"):
        reward = challenge.reward
        player_manager.award_xp(player, reward.xp)
        player_manager.award_gold(player, reward.gold)
        player_manager.complete_mission(player, challenge.challenge_id)

        if reward.title:
            player.story_flags["title"] = reward.title
        if reward.achievement:
            player_manager.unlock_achievement(player, reward.achievement)

        stat_bonuses = score_code(request.code, result)
        player_manager.award_stats(player, **stat_bonuses)

        if challenge.applies_stats and "user_variables" in result:
            player_manager.update_player_from_variables(player, result["user_variables"])
            judgment, dragon_narrative = player_manager.judge_stats(player)

            if judgment == "weak":
                player_manager.apply_blessing(player)
            elif judgment == "balanced":
                player_manager.apply_recognition(player)
            elif judgment == "overpowered":
                player.story_flags["dragon_trial_required"] = True
                
            player.story_flags["dragon_judgment_type"] = judgment
            player.story_flags["dragon_judgment_narrative"] = dragon_narrative

        await save_game(player, username)
    else:
        if request.challenge_id == "dragon_trial":
            player_manager.apply_reset(player)
            if "dragon_trial_required" in player.story_flags:
                del player.story_flags["dragon_trial_required"]
            player_manager.advance_scene(player, "chapter_1_trial_failed")
            await save_game(player, username)

            return {
                "success": False,
                "message": result.get("message", "You failed the Trial."),
                "output": result.get("output", ""),
                "test_results": result.get("test_results", []),
                "stat_bonuses": stat_bonuses,
                "player": player.model_dump(),
                "trial_failed": True
            }

    response = {
        "success": result.get("success", False),
        "message": result.get("message", ""),
        "output": result.get("output", ""),
        "test_results": result.get("test_results", []),
        "stat_bonuses": stat_bonuses,
        "player": player.model_dump(),
    }
    return response

@app.post("/api/advance")
async def advance_scene_route(request: AdvanceRequest, username: str = Depends(get_current_user), player: PlayerState = Depends(get_player_state)):
    refresh_content()

    if request.current_scene not in SCENES:
        raise HTTPException(status_code=404, detail="Scene not found")

    scene = SCENES[request.current_scene]
    next_scene = scene.next_scene
    
    for cond in scene.conditions:
        try:
            res = eval(cond.expression, {"__builtins__": {}}, {"player": player})
            if res:
                next_scene = cond.next_scene
                break
        except Exception as e:
            continue

    if not next_scene:
        return {"current_scene": None, "player": player.model_dump()}

    if next_scene not in SCENES:
        raise HTTPException(status_code=404, detail="Next scene not found")

    player_manager.advance_scene(player, next_scene)
    await save_game(player, username)

    response = {"current_scene": next_scene, "player": player.model_dump()}

    if request.current_scene == "chapter_1_dragon":
        j_type = player.story_flags.get("dragon_judgment_type")
        j_nar = player.story_flags.get("dragon_judgment_narrative")
        if j_type and j_nar:
            response["dragon_judgment"] = {
                "type": j_type,
                "narrative": j_nar
            }

    return response

@app.post("/api/save")
async def save(username: str = Depends(get_current_user), player: PlayerState = Depends(get_player_state)):
    await save_game(player, username)
    return {"message": "Game saved.", "filepath": f"db:{username}"}

@app.get("/api/load")
async def load(username: str = Depends(get_current_user), player: PlayerState = Depends(get_player_state)):
    return {"message": "Game loaded.", "player": player.model_dump()}

if __name__ == "__main__":
    import uvicorn
    # PORT is what most hosts inject; reload is for the developer's machine only.
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=os.environ.get("PYMAZE_RELOAD", "1") == "1",
    )
