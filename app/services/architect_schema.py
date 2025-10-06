from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ArchitectPlan(BaseModel):
    summary: str = ""
    suggested_steps: List[str] = Field(default_factory=list)
    suggested_env_flags: List[str] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    grounded_used: bool = False
    suggest_feature: bool = False
    feature_request: str | None = None
    tone_hint: str | None = None
