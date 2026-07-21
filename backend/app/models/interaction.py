"""Pydantic model for interaction JSON files loaded from interactions/*.json.

An interaction is a playable beat inside a scene — clicking chests open,
sorting values into type containers, predicting what print() will emit.
It sits between pure dialogue and a full coding challenge.

The engine deliberately knows nothing about any specific widget. `widget`
names a component in the frontend registry and `config` is passed to it
verbatim, so a new interaction type needs a new React component and a JSON
file — never a backend change.
"""
from typing import Any, Dict, Optional
from pydantic import BaseModel

from app.models.challenge import ChallengeReward


class InteractionDefinition(BaseModel):
    """Schema for a single interaction loaded from a .json file."""
    interaction_id: str
    widget: str                       # frontend registry key, e.g. "reveal_chests"
    title: str = ""
    prompt: str = ""                  # instruction shown above the widget
    config: Dict[str, Any] = {}       # widget-specific payload, opaque to the engine
    reward: Optional[ChallengeReward] = None
