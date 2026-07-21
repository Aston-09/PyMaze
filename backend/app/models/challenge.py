"""Pydantic models for challenge JSON files loaded from challenges/*.json."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ChallengeReward(BaseModel):
    """Rewards granted for completing this challenge."""
    xp: int = 0
    gold: int = 0
    title: Optional[str] = None
    achievement: Optional[str] = None


class ChallengeDefinition(BaseModel):
    """Schema for a single challenge loaded from a .json file."""
    challenge_id: str
    topic: str
    difficulty: str  # "tutorial", "easy", "medium", "hard", "boss"
    title: str
    narrative: str
    instructions: str
    starting_code: str

    # Execution configuration
    test_type: str = "script_variable"  # "function" | "script_variable" | "variables" | "script_output"
    function_name: Optional[str] = None
    input_variable: Optional[str] = None
    output_variable: Optional[str] = None

    # For "variables" test_type: which variables to check and their expected types
    expected_variables: Optional[Dict[str, str]] = None  # e.g. {"player_name": "str", "hp": "int"}

    # Character-creation challenges write their variables onto the player and
    # trigger the Dragon's Judgment. Keyed here rather than off test_type, so
    # that ordinary "variables" drills don't re-roll the player's stats.
    applies_stats: bool = False

    validation_tests: List[Dict[str, Any]] = []
    hints: List[str] = []
    reward: ChallengeReward = ChallengeReward()
