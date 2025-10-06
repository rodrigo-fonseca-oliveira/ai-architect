import json
import os
from typing import Any, Dict, List, Optional

from langchain.output_parsers import JsonOutputParser
from langchain.schema import BaseOutputParser

from app.utils.prompts import load_prompt
from .llm_client import LLMClient

# Helper to detect architect prompt schema and normalize JSON fields
ARCHITECT_STEP_KEYS = [
    "suggested_steps",
    "next_steps",
    "plan",
]
ARCHITECT_FLAG_KEYS = [
    "suggested_env_flags",
    "env_flags",
    "components",
]


def render_prompt(name: str, variables: Dict[str, Any] | None = None, version: Optional[str] = None) -> Dict[str, Any]:
    variables = variables or {}
    loaded = load_prompt(name, version=version)
    # Support two known schemas: {template} (query) and {prompt} (architect)
    template = loaded.get("template") or loaded.get("prompt") or ""

    # Simple Jinja-like replacement using Python format; keep deterministic
    # Support {{var}} placeholders by replacing with {var} for format()
    fmt = template.replace("{{", "{").replace("}}", "}")
    try:
        content = fmt.format(**variables)
    except Exception:
        content = template
    return {"version": loaded.get("version"), "content": content}


def run_prompt_as_chat(name: str, variables: Dict[str, Any], system: Optional[str] = None, version_env_var: Optional[str] = None) -> Dict[str, Any]:
    version = os.getenv(version_env_var) if version_env_var else None
    rendered = render_prompt(name, variables, version=version)

    # Optionally append format instructions for structured JSON
    use_structured = os.getenv("LC_USE_OUTPUT_PARSER", "false").lower() in ("1", "true", "yes", "on")
    format_instructions = None
    if use_structured and name in ("project_guide", "project_guide_brainstorm"):
        # Expect JSON object with certain keys
        format_instructions = (
            "Respond ONLY with a valid JSON object. Keys: "
            "summary (string, optional), suggested_steps (array of strings, optional), "
            "suggested_env_flags (array of strings, optional), next_steps (array of strings, optional), "
            "env_flags (array of strings, optional), plan (array of strings, optional), components (array of strings, optional)."
        )

    messages: List[Dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    if format_instructions:
        messages.append({"role": "system", "content": format_instructions})
    messages.append({"role": "user", "content": rendered["content"]})

    llm = LLMClient()
    result = llm.call(messages)
    # Attach audit metadata
    result["llm_provider"] = result.get("provider")
    result["llm_model"] = result.get("model")
    result["llm_tokens_prompt"] = result.get("tokens_prompt")
    result["llm_tokens_completion"] = result.get("tokens_completion")
    result["llm_cost_usd"] = result.get("cost_usd")
    result["prompt_version"] = f"{name}:{rendered.get('version')}"
    return result


def parse_json_safe(text: Any) -> Dict[str, Any]:
    # Fast-path: already a dict-like structure
    if isinstance(text, dict):
        return dict(text)
    if not isinstance(text, str):
        return {}
    raw = text.strip()

    # Strip common code fences (``` or ```json)
    if raw.startswith("```"):
        lines = raw.splitlines()
        # drop first fence line
        if lines:
            lines = lines[1:]
        # drop trailing fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    # Attempt direct JSON parse
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        return {"_": data}
    except Exception:
        pass

    # If the payload is a quoted JSON string (e.g., returned as a JSON string literal),
    # remove one level of surrounding quotes and unescape
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        inner = raw[1:-1]
        # Unescape common sequences
        inner = inner.replace('\\"', '"').replace("\\'", "'")
        inner = inner.replace("\\n", "\n").replace("\\t", "\t")
        try:
            data = json.loads(inner)
            if isinstance(data, dict):
                return data
            return {"_": data}
        except Exception:
            raw = inner  # fallthrough to other attempts

    # Try to fix overly escaped braces or backslashes
    try:
        candidate = raw
        # Sometimes extra backslashes remain; reduce double-escapes
        candidate = candidate.replace('\\\\', '\\')
        data = json.loads(candidate)
        if isinstance(data, dict):
            return data
        return {"_": data}
    except Exception:
        pass

    # Heuristic: extract first balanced JSON object substring and parse it after unescaping
    try:
        depth = 0
        start = -1
        for i, ch in enumerate(raw):
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start != -1:
                        sub = raw[start : i + 1]
                        sub_unescaped = (
                            sub.replace('\\"', '"')
                            .replace("\\'", "'")
                            .replace('\\n', '\n')
                            .replace('\\t', '\t')
                        )
                        data = json.loads(sub_unescaped)
                        if isinstance(data, dict):
                            return data
                        return {"_": data}
        # no balanced object found; fallthrough
    except Exception:
        pass

    # Last resort: try Python literal eval for dict-like strings
    try:
        import ast

        if raw.startswith("{") and raw.endswith("}"):
            coerced = ast.literal_eval(raw)
            if isinstance(coerced, dict):
                return {str(k): v for k, v in coerced.items()}
    except Exception:
        pass

    return {}


def extract_architect_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    steps: List[str] = []
    flags: List[str] = []
    summary: str = ""
    for k in ARCHITECT_STEP_KEYS:
        if k in data and isinstance(data[k], list):
            steps = [str(x) for x in data[k] if isinstance(x, (str, int, float))]
            break
    for k in ARCHITECT_FLAG_KEYS:
        if k in data and isinstance(data[k], list):
            flags = [str(x) for x in data[k] if isinstance(x, (str, int, float))]
            break
    if "summary" in data:
        summary = str(data.get("summary", ""))
    return {"steps": steps, "flags": flags, "summary": summary}


def parse_with_langchain_schema(text: Any) -> Dict[str, Any]:
    """
    Use LangChain's JsonOutputParser to enforce JSON object output.
    This is intentionally simple: we do not bind to a Pydantic model here to avoid tight coupling.
    """
    if not isinstance(text, str):
        return {}
    raw = text.strip()
    if not raw:
        return {}
    # JsonOutputParser expects valid JSON, but some models include markdown fences.
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    # Let JsonOutputParser parse; it raises on invalid input.
    parser: BaseOutputParser = JsonOutputParser()
    try:
        data = parser.parse(raw)
        if isinstance(data, dict):
            return data
        # If it parsed to a list or primitive, wrap for downstream mapping
        return {"_": data}
    except Exception:
        return {}
