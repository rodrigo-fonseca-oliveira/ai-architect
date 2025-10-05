import pytest

from app.utils.prompts import PromptNotFound, load_prompt


def test_load_latest_prompt():
    p = load_prompt("query")
    assert p["name"] == "query"
    assert p["version"] in ("v1", "v2")
    assert isinstance(p["template"], str) and p["template"]


def test_load_specific_version():
    p = load_prompt("query", version="v1")
    assert p["version"] == "v1"


def test_missing_version_raises():
    with pytest.raises(PromptNotFound):
        load_prompt("query", version="vX")


def test_missing_prompt_raises():
    with pytest.raises(PromptNotFound):
        load_prompt("nope")
