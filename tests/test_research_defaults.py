from app.schemas.research import AgentStep, Finding, ResearchResponse


def test_research_response_steps_default_isolation():
    f = [Finding(title="t", summary="s")]
    r1 = ResearchResponse(findings=f, sources=[], audit={})
    r2 = ResearchResponse(findings=f, sources=[], audit={})

    # Ensure steps defaults are independent lists
    assert r1.steps == []
    assert r2.steps == []
    r1.steps.append(
        AgentStep(
            name="search",
            inputs={"query": "q"},
            outputs={"results": ["o"]},
            latency_ms=1,
            hash="h",
            timestamp="2024-01-01T00:00:00Z",
        )
    )
    assert len(r1.steps) == 1
    assert r2.steps == []
