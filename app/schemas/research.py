from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=3)
    steps: Optional[List[str]] = Field(
        default_factory=lambda: ["search", "fetch", "summarize", "risk_check"]
    )
    user_id: Optional[str] = None


class AgentStep(BaseModel):
    name: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    latency_ms: int
    hash: str
    timestamp: str


class Finding(BaseModel):
    title: str
    summary: str
    url: Optional[str] = None


from pydantic import Field


class ResearchResponse(BaseModel):
    findings: List[Finding]
    sources: List[str]
    audit: Dict[str, Any]
    steps: List[AgentStep] = Field(default_factory=list)
