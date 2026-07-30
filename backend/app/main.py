"""
PyBe Backend API

Data-driven API that loads all content from external .scene and .json files.
The engine never contains story text — it reads, executes, and advances.
"""
import os
import json
from fastapi import FastAPI, HTTPException
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

# --- App Setup ---
app = FastAPI(title="PyBe Engine API")

# Comma-separated origins, e.g. PYBE_CORS_ORIGINS="https://pybe.example.com".
# Defaults to the local Vite dev server; "*" is accepted for throwaway demos.
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "PYBE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    # No cookies or auth headers cross-origin, so credentials stay off — which
    # is also what lets "*" remain a legal value here.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Authored content is reloaded whenever the files change, because
# `uvicorn --reload` only watches *.py — without this, editing a .scene leaves
# the running server serving a stale chapter with no visible sign of it.
_CONTENT = ContentStore({
    "scenes": (STORY_DIR, (".scene",), load_all_scenes),
    "challenges": (CHALLENGES_DIR, (".json",), load_all_challenges),
    "interactions": (INTERACTIONS_DIR, (".json",), load_all_interactions),
})


def refresh_content() -> None:
    """Pick up any edits to story/, challenges/ or interactions/."""
    global SCENES, CHALLENGES, INTERACTIONS
    if _CONTENT.refresh():
        SCENES = _CONTENT.data["scenes"]
        CHALLENGES = _CONTENT.data["challenges"]
        INTERACTIONS = _CONTENT.data["interactions"]
        print(f"[content] reloaded — {len(SCENES)} scenes, "
              f"{len(CHALLENGES)} challenges, {len(INTERACTIONS)} interactions")


def _registered_widgets() -> List[str]:
    """Widget names the frontend can render, from config/widgets.json."""
    try:
        with open(os.path.join(CONFIG_DIR, "widgets.json"), encoding="utf-8") as f:
            return json.load(f).get("widgets", [])
    except (OSError, json.JSONDecodeError):
        return []




# Surface authoring mistakes at startup instead of stranding a learner on a
# beat the UI cannot draw.
for _problem in validate_interactions(INTERACTIONS, _registered_widgets()):
    print(f"[interaction warning] {_problem}")
for _problem in validate_challenges(CHALLENGES):
    print(f"[challenge warning] {_problem}")

# Media is served straight off disk so authors can drop a background into
# assets/backgrounds/ and reference it by filename from a .scene — no build
# step, no import, no engine change.
if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
else:
    print(f"[asset warning] assets directory not found: {ASSETS_DIR}")


def _folder_frames(folder: str) -> List[str]:
    """Sorted animation-frame filenames directly inside `folder`, or []."""
    if not os.path.isdir(folder):
        return []
    return sorted(
        f for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"))
    )


def _art_frame_map() -> Dict[str, List[str]]:
    """Every animated stem the client can ask for, background or character,
    mapped to its ordered frame paths relative to ASSETS_DIR.

    A location lives at backgrounds/<stem>/frame_*.jpg; an NPC portrait at
    characters/<stem>/frame_*.jpg — the same `background:` tag in a .scene
    file reaches either, so switching a chapter to a character's own art is
    no different from switching it to a new place. The player is one folder
    deeper still, split by the appearance the learner picked at the start of
    the game: characters/player/<gender>/. Same drop-a-file philosophy
    throughout: no build step, no code change to add a new location or face.
    """
    out: Dict[str, List[str]] = {}

    bg_dir = os.path.join(ASSETS_DIR, "backgrounds")
    if os.path.isdir(bg_dir):
        for stem in os.listdir(bg_dir):
            frames = _folder_frames(os.path.join(bg_dir, stem))
            if frames:
                out[stem] = [f"backgrounds/{stem}/{f}" for f in frames]

    char_dir = os.path.join(ASSETS_DIR, "characters")
    if os.path.isdir(char_dir):
        for stem in os.listdir(char_dir):
            folder = os.path.join(char_dir, stem)
            if not os.path.isdir(folder):
                continue
            if stem == "player":
                for gender in ("male", "female"):
                    frames = _folder_frames(os.path.join(folder, gender))
                    if frames:
                        out[f"player_{gender}"] = [
                            f"characters/player/{gender}/{f}" for f in frames
                        ]
                continue
            frames = _folder_frames(folder)
            if frames:
                out[stem] = [f"characters/{stem}/{f}" for f in frames]

    return out


def _resolve_player_art(ref: Optional[str], player) -> Optional[str]:
    """`background: player` is gender-agnostic in the .scene file; resolve it
    to whichever sprite set the learner actually picked. Every other ref
    (a location, or an NPC's own name) passes through untouched."""
    if ref and os.path.splitext(ref)[0] == "player":
        return f"player_{player.gender or 'male'}"
    return ref


def _missing_backgrounds() -> List[str]:
    """Backgrounds (or character art) a scene asks for that aren't on disk.

    A missing file is a silent black screen at runtime, so it is worth one
    line at startup.
    """
    frame_map = _art_frame_map()
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


# --- Request/Response Models ---
class ExecuteRequest(BaseModel):
    code: str
    challenge_id: str


class AdvanceRequest(BaseModel):
    current_scene: str


class InteractionCompleteRequest(BaseModel):
    interaction_id: str


class AppearanceRequest(BaseModel):
    gender: str


# --- Routes ---

@app.get("/")
async def root():
    return {
        "message": "PyBe Engine API is running.",
        "story_dir": STORY_DIR,
        "challenges_dir": CHALLENGES_DIR,
        "scenes_loaded": list(SCENES.keys()),
        "challenges_loaded": list(CHALLENGES.keys()),
        "interactions_loaded": list(INTERACTIONS.keys()),
    }


@app.get("/api/scene/{scene_id}")
async def get_scene(scene_id: str):
    """Get a parsed scene by ID, with every challenge and interaction its beats
    reference, all rendered against the live player.

    Rendering happens here rather than at load time because the player's name
    and stats change as they play — the Wisdom chapter shows the learner their
    own character sheet, not a placeholder.
    """
    refresh_content()

    if scene_id not in SCENES:
        raise HTTPException(status_code=404, detail=f"Scene '{scene_id}' not found")

    scene = SCENES[scene_id]
    player = player_manager.get_player()
    response = render_for(scene.model_dump(), player)

    # A scene author writes `background: player` once, gender-agnostic; it
    # resolves here, against the live player, to whichever sprite set was
    # actually picked — same seam player_name templating already uses.
    if response.get("background"):
        response["background"] = _resolve_player_art(response["background"], player)
    for beat in response.get("beats", []):
        if beat.get("type") == "background":
            beat["ref"] = _resolve_player_art(beat.get("ref"), player)

    # Attach every definition the beat stream refers to.
    missions = [b.ref for b in scene.beats if b.type == "mission" and b.ref in CHALLENGES]
    interactions = [b.ref for b in scene.beats if b.type == "interactive" and b.ref in INTERACTIONS]

    response["challenges"] = {
        cid: render_for(CHALLENGES[cid].model_dump(), player) for cid in missions
    }
    response["interactions"] = {
        iid: render_for(INTERACTIONS[iid].model_dump(), player) for iid in interactions
    }

    # Legacy single-challenge field, still populated for older consumers.
    if scene.mission and scene.mission in CHALLENGES:
        response["challenge"] = response["challenges"][scene.mission]

    return response


@app.post("/api/interaction/complete")
async def complete_interaction(request: InteractionCompleteRequest):
    """Award an interaction's reward the first time the learner solves it.

    Replaying a scene should never farm XP, so the grant is idempotent —
    completion is tracked the same way missions are.
    """
    if request.interaction_id not in INTERACTIONS:
        raise HTTPException(
            status_code=404, detail=f"Interaction '{request.interaction_id}' not found"
        )

    interaction = INTERACTIONS[request.interaction_id]
    player = player_manager.get_player()
    already_done = request.interaction_id in player.completed_missions

    if not already_done:
        if interaction.reward:
            player_manager.award_xp(interaction.reward.xp)
            player_manager.award_gold(interaction.reward.gold)
            if interaction.reward.achievement:
                player_manager.unlock_achievement(interaction.reward.achievement)
        player_manager.complete_mission(request.interaction_id)
        save_game(player_manager.get_player())

    return {
        "awarded": not already_done,
        "reward": interaction.reward.model_dump() if interaction.reward else None,
        "player": player_manager.get_player().model_dump(),
    }


@app.get("/api/player")
async def get_player():
    """Return the current player state."""
    return player_manager.get_player().model_dump()


@app.post("/api/player/appearance")
async def set_player_appearance(request: AppearanceRequest):
    """One-time cosmetic pick: which player sprite set (male/female) shows
    up wherever a scene reflects the player's own art (`background: player`,
    e.g. the Sage's mirror). Not a stat, not taught by any mission — purely
    which of the two pre-drawn sprite sets to use."""
    if request.gender not in ("male", "female"):
        raise HTTPException(status_code=400, detail="gender must be 'male' or 'female'")
    player = player_manager.set_appearance(request.gender)
    save_game(player)
    return {"player": player.model_dump()}


@app.get("/api/backgrounds/frames")
async def background_frames():
    """Ordered animation frames for any scenario that has a folder of them —
    a location under backgrounds/, an NPC's own portrait under characters/,
    or the player's chosen appearance under characters/player/<gender>/.

    A folder like backgrounds/ancient_library/ holding frame_1.jpg, frame_2.jpg…
    is played as a looping cross-fade in the client. Same drop-a-file, no-build
    philosophy throughout — a stem with no folder just falls back to its
    single loose image under backgrounds/.
    """
    return _art_frame_map()


@app.post("/api/execute")
async def execute_code(request: ExecuteRequest):
    """Execute user code against a challenge's validation rules."""
    refresh_content()

    if request.challenge_id not in CHALLENGES:
        raise HTTPException(status_code=404, detail=f"Challenge '{request.challenge_id}' not found")

    challenge = CHALLENGES[request.challenge_id]

    # Validation tests are rendered against the player for the same reason the
    # scene text is: a challenge that asks the learner to print their own name
    # must expect *their* name, not the example the file was authored with.
    validation_tests = render_for(challenge.validation_tests, player_manager.get_player())

    # Run the executor
    result = execute_and_test(
        user_code=request.code,
        test_type=challenge.test_type,
        validation_tests=validation_tests,
        function_name=challenge.function_name,
        input_variable=challenge.input_variable,
        output_variable=challenge.output_variable,
        expected_variables=challenge.expected_variables,
    )

    # If the challenge passed, award rewards and score code quality
    stat_bonuses = {"int_bonus": 0, "wis_bonus": 0, "dex_bonus": 0}
    judgment = None
    dragon_narrative = None

    if result.get("success"):
        # Award challenge rewards
        reward = challenge.reward
        player_manager.award_xp(reward.xp)
        player_manager.award_gold(reward.gold)
        player_manager.complete_mission(challenge.challenge_id)

        if reward.title:
            player_manager.get_player().story_flags["title"] = reward.title
        if reward.achievement:
            player_manager.unlock_achievement(reward.achievement)

        # Score code quality for bonus stats
        stat_bonuses = score_code(request.code, result)
        player_manager.award_stats(**stat_bonuses)

        # Character-creation challenges write their variables onto the player and
        # trigger the Dragon's Judgment. Gated on `applies_stats`, not on
        # test_type — otherwise every later "variables" drill (the Wisdom
        # chapter has several) would re-roll the character and re-judge them.
        if challenge.applies_stats and "user_variables" in result:
            player_manager.update_player_from_variables(result["user_variables"])
            # Run Dragon's Judgment
            judgment, dragon_narrative = player_manager.judge_stats()

            if judgment == "weak":
                player_manager.apply_blessing()
            elif judgment == "balanced":
                player_manager.apply_recognition()
            # "overpowered" — for now, just flag it. Dragon Trial comes in Chapter 1.
            elif judgment == "overpowered":
                player_manager.get_player().story_flags["dragon_trial_required"] = True
                
            player_manager.get_player().story_flags["dragon_judgment_type"] = judgment
            player_manager.get_player().story_flags["dragon_judgment_narrative"] = dragon_narrative

        # Auto-save after success
        save_game(player_manager.get_player())
    else:
        # Failure mechanics for specific challenges
        if request.challenge_id == "dragon_trial":
            player_manager.apply_reset()
            # Remove flag so they don't loop back into the trial
            if "dragon_trial_required" in player_manager.get_player().story_flags:
                del player_manager.get_player().story_flags["dragon_trial_required"]
            # The client jumps straight to the failure scene, so record it
            # here too — otherwise a page reload would restore the player to
            # the trial they just failed, with their stats already reset.
            player_manager.advance_scene("chapter_1_trial_failed")
            save_game(player_manager.get_player())

            return {
                "success": False,
                "message": result.get("message", "You failed the Trial."),
                "output": result.get("output", ""),
                "test_results": result.get("test_results", []),
                "stat_bonuses": stat_bonuses,
                "player": player_manager.get_player().model_dump(),
                "trial_failed": True
            }

    # Build response
    response = {
        "success": result.get("success", False),
        "message": result.get("message", ""),
        "output": result.get("output", ""),
        "test_results": result.get("test_results", []),
        "stat_bonuses": stat_bonuses,
        "player": player_manager.get_player().model_dump(),
    }

    return response


@app.post("/api/advance")
async def advance_scene(request: AdvanceRequest):
    """Move the player to the next scene based on conditions."""
    refresh_content()

    if request.current_scene not in SCENES:
        raise HTTPException(status_code=404, detail=f"Scene '{request.current_scene}' not found")

    scene = SCENES[request.current_scene]
    player = player_manager.get_player()
    
    next_scene = scene.next_scene
    
    # Evaluate conditions
    for cond in scene.conditions:
        try:
            # Safely evaluate using player object in locals
            res = eval(cond.expression, {"__builtins__": {}}, {"player": player})
            if res:
                next_scene = cond.next_scene
                break
        except Exception as e:
            print(f"Error evaluating condition '{cond.expression}': {e}")
            continue

    if not next_scene:
        return {"current_scene": None, "player": player.model_dump()}

    if next_scene not in SCENES:
        raise HTTPException(status_code=404, detail=f"Next scene '{next_scene}' not found")

    player_manager.advance_scene(next_scene)
    save_game(player_manager.get_player())

    response = {"current_scene": next_scene, "player": player_manager.get_player().model_dump()}

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
async def save():
    """Manually save the game."""
    filepath = save_game(player_manager.get_player())
    return {"message": "Game saved.", "filepath": filepath}


@app.get("/api/load")
async def load():
    """Load the most recent save."""
    player = load_game()
    if player is None:
        return {"message": "No save found. Starting fresh.", "player": player_manager.get_player().model_dump()}

    # Restore the loaded state
    import app.engine.player_manager as pm
    pm._player = player
    return {"message": "Game loaded.", "player": player.model_dump()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
