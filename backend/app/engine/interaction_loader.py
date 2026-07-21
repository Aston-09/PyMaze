"""
Interaction Loader

Scans the interactions/ directory, loads all .json files, and indexes them by
interaction_id. Mirrors challenge_loader so authors get the same workflow:
drop a file in, restart, reference it from a .scene.
"""
import os
import json
import logging
from typing import Dict, List
from pydantic import ValidationError

from app.models.interaction import InteractionDefinition

log = logging.getLogger(__name__)


def load_all_interactions(interactions_dir: str) -> Dict[str, InteractionDefinition]:
    """Discover and load all interaction JSON files.

    A malformed file is skipped with a logged error rather than taking down the
    server at import time.
    """
    interactions: Dict[str, InteractionDefinition] = {}

    if not os.path.isdir(interactions_dir):
        log.warning("Interactions directory not found: %s", interactions_dir)
        return interactions

    for filename in sorted(os.listdir(interactions_dir)):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(interactions_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            interaction = InteractionDefinition(**data)
        except (json.JSONDecodeError, ValidationError, OSError) as exc:
            log.error("Skipping invalid interaction file %s: %s", filename, exc)
            continue

        if interaction.interaction_id in interactions:
            log.warning(
                "Duplicate interaction_id '%s' in %s — overwriting the earlier one.",
                interaction.interaction_id, filename,
            )
        interactions[interaction.interaction_id] = interaction

    return interactions


def validate_interactions(
    interactions: Dict[str, InteractionDefinition],
    known_widgets: List[str],
) -> List[str]:
    """Return authoring problems: a beat wired to a widget the UI cannot render
    would leave the learner staring at a dead scene, so surface it at startup."""
    problems: List[str] = []
    for iid, item in interactions.items():
        if item.widget not in known_widgets:
            problems.append(
                f"{iid}: unknown widget '{item.widget}' "
                f"(registered: {', '.join(sorted(known_widgets))})"
            )
    return problems
