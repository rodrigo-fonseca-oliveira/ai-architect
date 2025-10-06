import os
from typing import Any, Dict, List, Optional

# Provider-agnostic LLM client with safe offline stub by default.
# Returns a structured dict with text and audit metadata. When providers fail
# or are not configured, it falls back to a deterministic stub to keep tests stable.


class LLMClient:
    def __init__(self):
        self.provider = (os.getenv("LLM_PROVIDER", "stub") or "stub").lower()
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        try:
            self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))
        except Exception:
            self.temperature = 0.0
        try:
            self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "512"))
        except Exception:
            self.max_tokens = 512

    def _stub_call(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        prompt = "\n".join(m.get("content", "") for m in messages if m.get("role") != "system")
        text = (
            "[stub] This is a deterministic offline response. "
            + (prompt[:200] if isinstance(prompt, str) else "")
        )
        # Deterministic token estimates
        tp = max(1, len(prompt.split()))
        tc = max(1, min(self.max_tokens, len(text.split())))
        return {
            "text": text,
            "provider": "stub",
            "model": self.model,
            "tokens_prompt": tp,
            "tokens_completion": tc,
            "cost_usd": 0.0,
        }

    def call(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        provider = self.provider
        if provider == "stub":
            return self._stub_call(messages)
        try:
            if provider == "openai":
                from openai import OpenAI  # type: ignore

                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    return self._stub_call(messages)
                client = OpenAI(api_key=api_key)
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                choice = resp.choices[0]
                text = getattr(choice.message, "content", "") or ""
                tp = getattr(resp.usage, "prompt_tokens", None) or 0
                tc = getattr(resp.usage, "completion_tokens", None) or 0
                # Cost estimation is provider/model specific; best-effort zero unless configured elsewhere
                return {
                    "text": text,
                    "provider": provider,
                    "model": self.model,
                    "tokens_prompt": tp,
                    "tokens_completion": tc,
                    "cost_usd": 0.0,
                }
            if provider == "openrouter":
                import requests  # type: ignore

                api_key = os.getenv("OPENROUTER_API_KEY")
                if not api_key:
                    return self._stub_call(messages)
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                }
                r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=30)
                data = r.json()
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                tp = usage.get("prompt_tokens", 0)
                tc = usage.get("completion_tokens", 0)
                return {
                    "text": text,
                    "provider": provider,
                    "model": self.model,
                    "tokens_prompt": tp,
                    "tokens_completion": tc,
                    "cost_usd": 0.0,
                }
            if provider == "azure":
                # Azure OpenAI compatible API
                import requests  # type: ignore

                api_key = os.getenv("AZURE_OPENAI_API_KEY")
                endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
                deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT") or self.model
                if not api_key or not endpoint:
                    return self._stub_call(messages)
                url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-02-15-preview"
                headers = {
                    "api-key": api_key,
                    "Content-Type": "application/json",
                }
                payload = {
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                }
                r = requests.post(url, json=payload, headers=headers, timeout=30)
                data = r.json()
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                tp = usage.get("prompt_tokens", 0)
                tc = usage.get("completion_tokens", 0)
                return {
                    "text": text,
                    "provider": provider,
                    "model": deployment or self.model,
                    "tokens_prompt": tp,
                    "tokens_completion": tc,
                    "cost_usd": 0.0,
                }
        except Exception:
            # Last resort: stub
            return self._stub_call(messages)
        # Unknown provider -> stub
        return self._stub_call(messages)
