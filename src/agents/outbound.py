from pydantic import BaseModel, Field, ValidationError
from typing import Optional
import json
import re
from src.llm.ollama_runtime import OllamaChat


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
Company: X
Domain: XXX.com
Signal: expansion
Evidence URL: https://xyz.com/locations
Snippet: "We opened a new xxx in xxx on xxx"
Confidence: 0.72
OUTPUT:
{{"subject":"Congrats on your X opening","body":"Hi xxx — noticed your new xxx opened xx. \n\\nWould a 10-minute walkthrough next week be useful?","call_to_action":"Open to a 10-minute walkthrough next week?"}}

INPUT:
Company: {company}
Domain: {domain}
Signal: {signal_type}
Evidence URL: {url}
Snippet: "{snippet}"
Confidence: {confidence}
OUTPUT (JSON only):"""


def draft_from_card(llm: OllamaChat, *, company: str, domain: str, signal_type: str, url: str, snippet: str, confidence: float):
    user = TEMPLATE.format(company=company or "Prospect", domain=domain,
                           signal_type=signal_type, url=url, snippet=snippet, confidence=confidence)
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": user}]

    print(f"DEBUG OUTBOUND: Drafting email for {company}")
    print(f"DEBUG OUTBOUND: Signal: {signal_type}, Snippet: {snippet}")

    out = llm.chat(messages).strip()
    print(f"DEBUG OUTBOUND: LLM response: {out[:200]}...")
    # helper: replace common example placeholders (X, xxx, xx) with the real company
    placeholder_pattern = re.compile(r"\b(?:X|xxx|xx)\b", flags=re.IGNORECASE)

    def _replace_placeholders_in_data(data_dict: dict, company_name: str):
        for key in ("subject", "body", "call_to_action"):
            if key in data_dict and isinstance(data_dict[key], str):
                new_val = placeholder_pattern.sub(company_name, data_dict[key])
                if new_val != data_dict[key]:
                    print(
                        f"DEBUG OUTBOUND: Replaced placeholders in '{key}': '{data_dict[key]}' -> '{new_val}'")
                data_dict[key] = new_val
        return data_dict

    def _sanitize_json_like_string(s: str) -> str:
        # Escape raw newline and carriage return characters that appear inside
        # JSON string literals but are not escaped. This often happens when the LLM
        # returns pretty-printed or unescaped newlines inside quotes.
        out_chars = []
        in_str = False
        escape = False
        for ch in s:
            if ch == '"' and not escape:
                in_str = not in_str
                out_chars.append(ch)
                continue
            if ch == '\\' and not escape:
                escape = True
                out_chars.append(ch)
                continue
            if ch in ('\n', '\r') and in_str and not escape:
                # replace actual newline with escaped sequence
                out_chars.append('\\n')
                escape = False
                continue
            out_chars.append(ch)
            escape = False
        return ''.join(out_chars)

    json_match = re.search(r'\{[^{}]*"subject"[^{}]*\}', out, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            print(f"DEBUG OUTBOUND: Parsed JSON: {data}")
            data = _replace_placeholders_in_data(data, company or "Prospect")
            return EmailDraft.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"DEBUG OUTBOUND: JSON parse error: {e}")
            # Try sanitizing the JSON-like string (escape raw newlines inside quoted strings)
            try:
                sanitized = _sanitize_json_like_string(json_match.group(0))
                print(
                    f"DEBUG OUTBOUND: Sanitized JSON string (first 200 chars): {sanitized[:200]}")
                data = json.loads(sanitized)
                print(
                    f"DEBUG OUTBOUND: Parsed JSON after sanitization: {data}")
                data = _replace_placeholders_in_data(
                    data, company or "Prospect")
                return EmailDraft.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e2:
                print(
                    f"DEBUG OUTBOUND: JSON parse error after sanitization: {e2}")

    # fallback pattern
    m = re.search(r"\{.*\}\s*$", out, flags=re.S)
    if m:
        try:
            data = json.loads(m.group(0))
            print(f"DEBUG OUTBOUND: Parsed JSON (fallback): {data}")
            data = _replace_placeholders_in_data(data, company or "Prospect")
            return EmailDraft.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"DEBUG OUTBOUND: Fallback JSON parse error: {e}")
            try:
                sanitized = _sanitize_json_like_string(m.group(0))
                print(
                    f"DEBUG OUTBOUND: Sanitized fallback JSON string (first 200 chars): {sanitized[:200]}")
                data = json.loads(sanitized)
                print(
                    f"DEBUG OUTBOUND: Parsed JSON (fallback) after sanitization: {data}")
                data = _replace_placeholders_in_data(
                    data, company or "Prospect")
                return EmailDraft.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e2:
                print(
                    f"DEBUG OUTBOUND: Fallback JSON parse error after sanitization: {e2}")

 
    return EmailDraft(
        subject=f"Quick idea after {company or 'your'} recent update",
        body=f"Hi {company or ''} — noticed: {snippet}\n\nWe help teams act on this signal. Open to a 10-minute walkthrough?",
        call_to_action="Open to a 10-minute walkthrough?"
    )
