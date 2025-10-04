from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from .session import Base


class Audit(Base):
    __tablename__ = "audit"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, index=True, nullable=False)
    endpoint = Column(String, index=True, nullable=False)
    user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    tokens_prompt = Column(Integer, nullable=True)
    tokens_completion = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    compliance_flag = Column(Boolean, default=False)
    prompt_hash = Column(String, nullable=True)
    response_hash = Column(String, nullable=True)
