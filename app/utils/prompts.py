import os
import yaml
from typing import Dict, Any, Optional

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "prompts")


class PromptNotFound(Exception):
    pass


def load_prompt(name: str, version: Optional[str] = None) -> Dict[str, Any]:
    path = os.path.join(PROMPTS_DIR, f"{name}.yaml")
    if not os.path.exists(path):
        raise PromptNotFound(f"prompt file not found: {name}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or data.get("name") != name:
        raise PromptNotFound(f"invalid prompt file: {name}")

    versions = data.get("versions", [])
    if not versions:
        raise PromptNotFound(f"no versions in prompt: {name}")

    if version is None:
        # latest is the last item
        entry = versions[-1]
    else:
        entry = next((v for v in versions if v.get("version") == version), None)
        if entry is None:
            raise PromptNotFound(f"version not found: {name}:{version}")
    return {
        "name": name,
        "version": entry.get("version"),
        "metadata": entry.get("metadata", {}),
        "template": entry.get("template", ""),
    }
