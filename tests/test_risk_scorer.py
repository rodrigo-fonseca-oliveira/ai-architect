from app.services.risk_scorer import heuristic_score


def test_heuristic_risk_scoring():
    low = heuristic_score("Informational update only")
    assert low["label"] == "low"

    med = heuristic_score("We detected a vulnerability and an incident")
    assert med["label"] in ("medium", "high")

    high = heuristic_score("Critical breach and violation, potential lawsuit")
    assert high["label"] == "high"
