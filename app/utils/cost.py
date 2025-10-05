from typing import Tuple

# Very rough token and cost estimate for Phase 0
# Prices are illustrative only
PRICES_PER_1K = {
    "gpt-4o-mini": (0.15, 0.60),  # (prompt, completion) USD per 1k tokens
    "gpt-4.1": (5.0, 15.0),
    "stub": (0.0, 0.0),
}


def estimate_tokens_and_cost(
    model: str, prompt: str, completion: str
) -> Tuple[int, int, float]:
    tp = max(1, len(prompt) // 4)  # crude: ~4 chars per token
    tc = max(1, len(completion) // 4)
    price = PRICES_PER_1K.get(model, PRICES_PER_1K.get("gpt-4o-mini"))
    cost = (tp / 1000.0) * price[0] + (tc / 1000.0) * price[1]
    return tp, tc, cost
