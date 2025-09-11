import json, re
from typing import Dict, List
from pydantic import ValidationError
from src.llm.ollama_runtime import OllamaChat
from src.schemas import ValidateResult

SYSTEM = f"""
You are a verification agent. You will receive several HTML pages from one domain.
Find ONE strong signal (expansion/scheduler/hiring) and return FINAL JSON:
{ValidateResult.model_json_schema()}

Rules:
- Use only provided pages; do not fetch.
- Provide evidence_url (one of the provided URLs), a short snippet, and published_at if visible.
- If uncertain, return ok=false with a brief 'why'.
- FINAL JSON only.
"""

def run_validator_agent(
    domain: str,
    pages: Dict[str, str],
    urls: Dict[str, str],
    patterns: Dict[str, List[str]],
    *,
    llm: OllamaChat,
    step_limit=4
) -> ValidateResult:
    hints = json.dumps(patterns, indent=2)
    pages_condensed = "\n".join([f"PATH: {p}\nHTML:\n{pages[p][:5000]}" for p in pages])  # truncate
    messages = [
        {"role":"system","content":SYSTEM},
        {"role":"user","content":(
            f"Domain: {domain}\n"
            f"URL map: {urls}\n"
            f"Signal hints: {hints}\n"
            f"Pages (truncated):\n{pages_condensed}\n"
            "Decide the single strongest signal. Return FINAL JSON only."
        )}
    ]
    for _ in range(step_limit):
        out = llm.chat(messages).strip()
        m = re.search(r"\{.*\}\s*$", out, flags=re.S)
        if m:
            try:
                return ValidateResult.model_validate_json(m.group(0))
            except ValidationError:
                messages.append({"role":"assistant","content":out}); continue
        messages.append({"role":"assistant","content":out})
    return ValidateResult(ok=False, why=["step_limit_exceeded"])
