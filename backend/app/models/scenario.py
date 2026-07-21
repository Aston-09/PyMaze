from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ScenarioStep(BaseModel):
    step_id: int
    title: str
    narrative: str
    instructions: str
    starting_code: str
    validation_tests: List[Dict[str, Any]]
    test_type: str = "function" # "function" or "script_variable"
    input_variable: Optional[str] = None
    output_variable: Optional[str] = None

class ScenarioContext(BaseModel):
    scenario_id: str
    title: str
    description: str
    steps: List[ScenarioStep]

class UserSession(BaseModel):
    session_id: str
    current_scenario_id: Optional[str] = None
    current_step_id: int = 1
    completed_scenarios: List[str] = []

class ExecuteRequest(BaseModel):
    session_id: str
    code: str
    scenario_id: str
    step_id: int

class ExecuteResponse(BaseModel):
    success: bool
    message: str
    output: Optional[str] = None
    test_results: List[Dict[str, Any]] = []
