from pydantic import BaseModel, Field, ValidationError
from typing import Optional
import json, re
from src.llm.ollama_runtime import OllamaChat, OllamaConfig


class EmailDraft(BaseModel):
    subject: str = Field(..., max_length=120)
    body: str
    call_to_action: Optional[str] = None

SYSTEM = """You are a concise SDR assistant.
Return ONLY a JSON object exactly like:
{"subject":"...", "body":"...", "call_to_action":"..."}

Rules:
- Subject ≤ 60 chars, specific to the signal.
- Body: 3 short paragraphs max (<= 80 words total).
- First line: reference the signal explicitly (what/where/when).
- Avoid hype, no emojis, no bullet lists, no links.
- Use the CTA verbatim if provided; otherwise write one clear ask."""

TEMPLATE = """Example (style guide only):
INPUT:
Company: Acme Dental
Domain: acme.com
Signal: expansion
Evidence URL: https://acme.com/locations
Snippet: "We opened a new clinic in Dallas on Sept 1, 2025."
Confidence: 0.72
OUTPUT:
{{"subject":"Congrats on your Dallas opening","body":"Hi Acme Dental — noticed your new Dallas clinic opened Sept 1. Many practices see a brief surge in new-patient interest after expansion.\\n\\nTeams use Orbital-style workflows to route form fills in real time and book visits faster.\\n\\nWould a 10-minute walkthrough next week be useful?","call_to_action":"Open to a 10-minute walkthrough next week?"}}

INPUT:
Company: {company}
Domain: {domain}
Signal: {signal_type}
Evidence URL: {url}
Snippet: "{snippet}"
Confidence: {confidence}
OUTPUT (JSON only):"""

def draft_from_card(llm: OllamaChat, *, company: str, domain: str, signal_type: str, url: str, snippet: str, confidence: float):
    user = TEMPLATE.format(company=company or "Prospect", domain=domain, signal_type=signal_type, url=url, snippet=snippet, confidence=confidence)
    messages = [{"role":"system","content":SYSTEM},{"role":"user","content":user}]
    
    print(f"DEBUG OUTBOUND: Drafting email for {company}")
    print(f"DEBUG OUTBOUND: Signal: {signal_type}, Snippet: {snippet}")
    
    out = llm.chat(messages).strip()
    print(f"DEBUG OUTBOUND: LLM response: {out[:200]}...")
    
    # Try to find JSON in the response
    json_match = re.search(r'\{[^{}]*"subject"[^{}]*\}', out, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            print(f"DEBUG OUTBOUND: Parsed JSON: {data}")
            return EmailDraft.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"DEBUG OUTBOUND: JSON parse error: {e}")
    
    # Fallback: try the original pattern
    m = re.search(r"\{.*\}\s*$", out, flags=re.S)
    if m:
        try:
            data = json.loads(m.group(0))
            print(f"DEBUG OUTBOUND: Parsed JSON (fallback): {data}")
            return EmailDraft.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"DEBUG OUTBOUND: Fallback JSON parse error: {e}")
    
    # Final fallback
    print("DEBUG OUTBOUND: Using fallback email")
    return EmailDraft(
        subject="Quick idea after your recent update", 
        body=f"Hi — noticed: {snippet}\n\nWe help teams act on this signal. Open to a 10-minute walkthrough?", 
        call_to_action="Open to a 10-minute walkthrough?"
    )
