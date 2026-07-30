"""Lightweight cost tracking for LLM API calls."""

_pipeline_cost = {"scoring": 0.0, "writing": 0.0, "editorial_room": 0.0, "linkedin": 0.0, "other": 0.0}

def track_llm_cost(category: str, estimated_tokens: int = 1000):
    cost_per_1k = 0.0007 if category in ("writing", "linkedin") else 0.00027
    _pipeline_cost.setdefault(category, 0.0)
    _pipeline_cost[category] += (estimated_tokens / 1000) * cost_per_1k

def get_costs() -> dict:
    total = sum(_pipeline_cost.values())
    return {"breakdown": dict(_pipeline_cost), "total": round(total, 4), "estimated": True}

def reset_costs():
    global _pipeline_cost
    _pipeline_cost = {"scoring": 0.0, "writing": 0.0, "editorial_room": 0.0, "linkedin": 0.0, "other": 0.0}
