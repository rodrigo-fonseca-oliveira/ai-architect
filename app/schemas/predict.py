from typing import Dict, Any, Optional
from pydantic import BaseModel


class PredictRequest(BaseModel):
    user_id: Optional[str] = None
    features: Dict[str, Any]


class PredictResponse(BaseModel):
    prediction: Any
    model_version: str
    metrics: Dict[str, float] = {}
    audit: Dict[str, Any]
