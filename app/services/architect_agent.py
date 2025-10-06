import os
from typing import Any, Dict, List, Tuple

from langchain.output_parsers import PydanticOutputParser
from app.services.llm_client import LLMClient
from app.services.architect_schema import ArchitectPlan
from app.services.langchain_rag import answer_with_citations


def _build_messages(question: str, plan_parser: PydanticOutputParser, context_blocks: List[str] | None = None) -> List[Dict[str, str]]:
    context_blocks = context_blocks or []
    fmt = plan_parser.get_format_instructions()
    system = (
        "You are the solution architect assistant for the AI-Risk-Monitor project. "
        "Respond ONLY with a JSON object that matches the provided schema."
    )
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "system", "content": fmt},
    ]
    if context_blocks:
        ctx = "\n\n".join(context_blocks[:3])  # keep concise
        messages.append({"role": "system", "content": f"Context (for grounding):\n{ctx}"})
    messages.append({"role": "user", "content": question})
    return messages


def run_architect_agent(question: str, session_id: str | None = None, user_id: str | None = None) -> Tuple[ArchitectPlan, Dict[str, Any]]:
    # 1) Retrieval
    citations: List[Dict[str, Any]] = []
    rag_meta: Dict[str, Any] = {}

    docs_path = os.getenv("DOCS_PATH") or "./docs"
    os.environ["DOCS_PATH"] = docs_path
    rag = answer_with_citations(question, k=3)
    citations = rag.get("citations", [])
    for k in ("rag_multi_query", "rag_multi_count", "rag_hyde"):
        if k in rag:
            rag_meta[k] = rag[k]

    grounded_used = bool(citations)
    context_blocks: List[str] = []
    if grounded_used:
        # Make compact context lines
        for c in citations[:3]:
            title = c.get("source") or c.get("path") or "doc"
            snippet = (c.get("snippet") or "").strip().replace("\n", " ")
            if snippet:
                snippet = snippet[:400]
            context_blocks.append(f"- {title}: {snippet}")

    # 2) Build messages with structured format instructions
    parser = PydanticOutputParser(pydantic_object=ArchitectPlan)
    messages = _build_messages(question, parser, context_blocks if grounded_used else None)

    # 3) Call LLM
    llm = LLMClient()
    result = llm.call(messages)

    # 4) Parse structured output (fallback to defaults on error)
    text = result.get("text") or ""
    try:
        plan = parser.parse(text)
    except Exception:
        # fallback: try to construct directly if text is already JSON-like
        try:
            import json as _json

            data = _json.loads(text) if isinstance(text, str) else {}
            plan = ArchitectPlan(**data) if isinstance(data, dict) else ArchitectPlan()
        except Exception:
            plan = ArchitectPlan()

    # 5) Attach citations if grounded
    if grounded_used:
        plan.citations = citations
        plan.grounded_used = True

    # Light heuristic for feature suggestion
    try:
        ql = (question or "").lower()
        needs = any(w in ql for w in ("feature", "support", "integrate", "add", "roadmap"))
        sparse = len(plan.suggested_steps or []) == 0 and len(plan.suggested_env_flags or []) == 0
        if (sparse or not grounded_used) and needs:
            plan.suggest_feature = True
            plan.feature_request = plan.feature_request or (
                f"Request: {question[:60]}" if question else "Feature request"
            )
            plan.tone_hint = plan.tone_hint or ("exploratory" if not grounded_used else "actionable")
    except Exception:
        pass

    # 6) Build audit fields
    audit: Dict[str, Any] = {
        "llm_provider": result.get("provider"),
        "llm_model": result.get("model"),
        "llm_tokens_prompt": result.get("tokens_prompt"),
        "llm_tokens_completion": result.get("tokens_completion"),
        "llm_cost_usd": result.get("cost_usd"),
        **rag_meta,
    }

    return plan, audit
