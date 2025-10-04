import itertools

from app.utils.rbac import is_allowed_agent_step


def test_rbac_agent_steps_matrix():
    roles = ["guest", "analyst", "admin", "unknown"]
    steps = ["fetch", "search", "summarize", "risk_check", "unknown_step"]

    expected = {
        ("guest", "fetch"): False,
        ("guest", "search"): False,
        ("guest", "summarize"): False,
        ("guest", "risk_check"): True,
        ("analyst", "fetch"): True,
        ("analyst", "search"): True,
        ("analyst", "summarize"): True,
        ("analyst", "risk_check"): True,
        ("admin", "fetch"): True,
        ("admin", "search"): True,
        ("admin", "summarize"): True,
        ("admin", "risk_check"): True,
        # Unknown steps should be denied for all roles
        ("guest", "unknown_step"): False,
        ("analyst", "unknown_step"): False,
        ("admin", "unknown_step"): False,
        ("unknown", "unknown_step"): False,
    }

    for role, step in itertools.product(roles, steps):
        assert is_allowed_agent_step(role, step) == expected.get((role, step), False)
