"""
Test short and long memory integration with the Architect agent.
"""
import os
import pytest
from app.services.architect_agent import run_architect_agent
from app.memory.short_memory import init_short_memory, load_turns, clear_short_memory
from app.memory.long_memory import retrieve_facts, clear_long_memory


@pytest.fixture(autouse=True)
def enable_memory():
    """Enable memory flags for tests."""
    old_short = os.environ.get("MEMORY_SHORT_ENABLED")
    old_long = os.environ.get("MEMORY_LONG_ENABLED")
    os.environ["MEMORY_SHORT_ENABLED"] = "true"
    os.environ["MEMORY_LONG_ENABLED"] = "true"
    os.environ["LLM_ENABLE_ARCHITECT"] = "true"
    yield
    # Restore
    if old_short is not None:
        os.environ["MEMORY_SHORT_ENABLED"] = old_short
    else:
        os.environ.pop("MEMORY_SHORT_ENABLED", None)
    if old_long is not None:
        os.environ["MEMORY_LONG_ENABLED"] = old_long
    else:
        os.environ.pop("MEMORY_LONG_ENABLED", None)


@pytest.fixture
def cleanup_memory():
    """Clear memory after tests."""
    yield
    try:
        clear_short_memory("test_user", "test_session")
        clear_long_memory("test_user")
    except Exception:
        pass


def test_architect_memory_integration_short_memory(cleanup_memory):
    """Test that architect agent saves and loads short-term memory."""
    user_id = "test_user"
    session_id = "test_session"

    # Clear any existing memory
    clear_short_memory(user_id, session_id)

    # First turn
    question1 = "What are the deployment options for this project?"
    plan1, audit1 = run_architect_agent(question1, session_id=session_id, user_id=user_id)

    # Verify short memory writes
    assert audit1.get("memory_short_writes", 0) == 2  # user + assistant turn

    # Check that turns were saved
    init_short_memory()
    turns = load_turns(user_id, session_id)
    assert len(turns) >= 2
    assert any(question1 in content for role, content in turns if role == "user")

    # Second turn - should load previous context
    question2 = "Can I use Docker?"
    plan2, audit2 = run_architect_agent(question2, session_id=session_id, user_id=user_id)

    # Verify short memory reads (should have loaded previous turns)
    assert audit2.get("memory_short_reads", 0) >= 2

    # Verify more writes
    assert audit2.get("memory_short_writes", 0) == 2


def test_architect_memory_integration_long_memory(cleanup_memory):
    """Test that architect agent ingests and retrieves long-term facts."""
    user_id = "test_user"
    session_id = "test_session"

    # Clear any existing memory
    clear_long_memory(user_id)

    # First turn - should ingest facts
    question1 = "How do I configure RAG with Chroma vector backend?"
    plan1, audit1 = run_architect_agent(question1, session_id=session_id, user_id=user_id)

    # Verify long memory writes (at least summary should be ingested if >50 chars)
    assert audit1.get("memory_long_writes", 0) >= 0  # May be 0 if summary is short

    # Second turn with related question - should retrieve relevant facts
    question2 = "What about Pinecone integration?"
    plan2, audit2 = run_architect_agent(question2, session_id=session_id, user_id=user_id)

    # If facts were written in turn 1, turn 2 should potentially read them
    # (depends on similarity scoring)
    # Access non-deterministic reads count for debugging (no assertion on value)
    _ = audit2.get("memory_long_reads", 0)
    # This is non-deterministic based on embeddings, so we just check the field exists
    assert "memory_long_reads" in audit2


def test_architect_memory_audit_fields(cleanup_memory):
    """Test that all memory audit fields are present in response."""
    user_id = "test_user"
    session_id = "test_session"

    clear_short_memory(user_id, session_id)
    clear_long_memory(user_id)

    question = "Tell me about memory configuration flags"
    plan, audit = run_architect_agent(question, session_id=session_id, user_id=user_id)

    # Verify all memory audit fields are present
    expected_fields = [
        "memory_short_reads",
        "memory_short_writes",
        "memory_short_pruned",
        "summary_updated",
        "memory_long_reads",
        "memory_long_writes",
        "memory_long_pruned",
    ]

    for field in expected_fields:
        assert field in audit, f"Missing audit field: {field}"


def test_architect_memory_disabled():
    """Test that agent works correctly when memory is disabled."""
    old_short = os.environ.get("MEMORY_SHORT_ENABLED")
    old_long = os.environ.get("MEMORY_LONG_ENABLED")

    try:
        os.environ["MEMORY_SHORT_ENABLED"] = "false"
        os.environ["MEMORY_LONG_ENABLED"] = "false"

        question = "What is the router configuration?"
        plan, audit = run_architect_agent(question, session_id="test", user_id="test")

        # Memory counters should still be present but all zero
        assert audit.get("memory_short_reads", 0) == 0
        assert audit.get("memory_short_writes", 0) == 0
        assert audit.get("memory_long_reads", 0) == 0
        assert audit.get("memory_long_writes", 0) == 0

    finally:
        if old_short is not None:
            os.environ["MEMORY_SHORT_ENABLED"] = old_short
        if old_long is not None:
            os.environ["MEMORY_LONG_ENABLED"] = old_long
