"""
PyMaze Backend API

Data-driven API that loads all content from external .scene and .json files.
"""
import os
import json
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.engine.story_loader import load_all_scenes
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

# --- App Setup ---
app = FastAPI(title="PyMaze Engine API")

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

SCENES = load_all_scenes(STORY_DIR)
CHALLENGES = load_all_challenges(CHALLENGES_DIR)
INTERACTIONS = load_all_interactions(INTERACTIONS_DIR)

_CONTENT = ContentStore({
    "scenes": (STORY_DIR, (".scene",), load_all_scenes),
    "challenges": (CHALLENGES_DIR, (".json",), load_all_challenges),
    "interactions": (INTERACTIONS_DIR, (".json",), load_all_interactions),
})


def refresh_content() -> None:
    global SCENES, CHALLENGES, INTERACTIONS
    if _CONTENT.refresh():
        SCENES = _CONTENT.data["scenes"]
        CHALLENGES = _CONTENT.data["challenges"]
        INTERACTIONS = _CONTENT.data["interactions"]
        print(f"[content] reloaded — {len(SCENES)} scenes, "
              f"{len(CHALLENGES)} challenges, {len(INTERACTIONS)} interactions")


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


def _missing_backgrounds() -> List[str]:
    """Backgrounds a scene asks for that aren't on disk.

    A missing file is a silent black screen at runtime, so it is worth one
    line at startup.
    """
    bg_dir = os.path.join(ASSETS_DIR, "backgrounds")
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
async def get_player():
    """Return the current player state."""
    return player_manager.get_player().model_dump()


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
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
