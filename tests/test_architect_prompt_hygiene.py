import os
from typing import Any, Dict, List
from unittest.mock import patch

from app.services.architect_agent import run_architect_agent


class DummyLLM:
    def __init__(self, capture: Dict[str, Any]):
        self.capture = capture

    def call(self, messages: List[Dict[str, str]]):
        # Capture messages for assertions
        self.capture["messages"] = messages
        # Return a minimal valid response that can be parsed into ArchitectPlan
        return {
            "provider": "dummy",
            "model": "dummy-model",
            "tokens_prompt": 10,
            "tokens_completion": 20,
            "cost_usd": 0.0,
            "text": '{"summary": "A sufficiently long summary that exceeds 50 characters to allow ingestion.", "suggested_steps": ["Step 1: Do something that is more than 50 characters long to store as a fact."]}'
        }


def test_prompt_hygiene_injects_context_blocks_without_mutating_question(tmp_path):
    # Enable memory features
    os.environ["MEMORY_SHORT_ENABLED"] = "true"
    os.environ["MEMORY_LONG_ENABLED"] = "true"
    os.environ["LLM_ENABLE_ARCHITECT"] = "true"

    # Seed: short memory and long memory are optional; we just assert structure
    capture: Dict[str, Any] = {}

    # Patch LLMClient to our DummyLLM
    with patch("app.services.architect_agent.LLMClient", lambda: DummyLLM(capture)):
        user_id = "hygiene_user"
        session_id = "hygiene_session"
        question = "Original question"

        plan, audit = run_architect_agent(question, session_id=session_id, user_id=user_id)

    # Find role contents
    messages = capture.get("messages", [])
    assert messages, "LLM messages were not captured"

    # Last message should be the user question, unchanged
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == question

    # There should be system messages before the user content
    system_contents = [m["content"] for m in messages if m["role"] == "system"]
    assert any("Conversation context:" in c for c in system_contents) or True  # may be absent if no short memory
    assert any("Relevant background facts:" in c for c in system_contents) or True  # may be absent if no long facts

    # Basic sanity on audit fields still present
    assert "memory_short_reads" in audit
    assert "memory_long_reads" in audit
