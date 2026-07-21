"""Pydantic models for parsed .scene DSL files."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class SceneDialogue(BaseModel):
    """A block of dialogue spoken by an NPC or narrator."""
    speaker: str  # "narrator" for plain dialogue:, or NPC name
    lines: List[str]


class SceneReward(BaseModel):
    """Rewards granted after completing a scene's mission."""
    xp: int = 0
    gold: int = 0
    title: Optional[str] = None
    achievement: Optional[str] = None


class SceneCondition(BaseModel):
    """A conditional branch: if expression is true, go to next_scene."""
    expression: str
    next_scene: str


class SceneBeat(BaseModel):
    """One playable step of a scene, in authored order.

    A scene is a stream of beats rather than "all the dialogue, then the
    mission". That ordering is what lets a chapter teach, interact, teach,
    then test — and it is why a single scene can hold more than one mission.
    """
    type: str                          # "dialogue" | "system" | "interactive" | "mission" | "background"
    speaker: Optional[str] = None      # dialogue only
    lines: List[str] = []              # dialogue: prose. system: [title, ...body]
    ref: Optional[str] = None          # interaction_id, challenge_id, background filename, or system variant


class ParsedScene(BaseModel):
    """The fully parsed representation of a single @scene block."""
    scene_id: str
    background: Optional[str] = None
    music: Optional[str] = None
    beats: List[SceneBeat] = []
    # `dialogues` and `mission` are the pre-beats shape, kept so older scenes
    # and any existing consumer keep working unchanged (rulebook rule 6).
    dialogues: List[SceneDialogue] = []
    mission: Optional[str] = None  # challenge_id reference (first mission beat)
    reward: Optional[SceneReward] = None
    conditions: List[SceneCondition] = []
    next_scene: Optional[str] = None
