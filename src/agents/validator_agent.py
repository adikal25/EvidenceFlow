import json, re
from typing import Dict, List
from pydantic import ValidationError
from src.llm.ollama_runtime import OllamaChat
from src.schemas import ValidateResult
from src.tools.web import extract_text

SYSTEM = f"""
You are a verification agent. You will receive text content from web pages.
Find ONE strong signal (expansion/scheduler/hiring) and return FINAL JSON.

Rules:
- Look for business signals in the provided text
- Provide evidence_url (one of the provided URLs), a short snippet, and published_at if visible
- If uncertain, return ok=false with a brief 'why'
- Return ONLY the final JSON result, not the schema

Signal types:
- expansion: new locations, grand openings, expansion announcements
- scheduler: booking systems, appointment scheduling, calendar tools
- hiring: job postings, career opportunities, hiring announcements

Example response:
{{"ok": true, "signal_type": "expansion", "evidence_url": "http://example.com/", "snippet": "We are excited to announce our new location opening", "published_at": null, "confidence": 0.8, "why": []}}
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
    print(f"DEBUG VALIDATOR: Starting validation for {domain}")
    print(f"DEBUG VALIDATOR: Pages available: {list(pages.keys())}")
    print(f"DEBUG VALIDATOR: Patterns: {patterns}")
    
    # Extracting text from HTML pages
    text_pages = {}
    for path, html in pages.items():
        try:
            text = extract_text(html)
            text_pages[path] = text
            print(f"DEBUG VALIDATOR: Extracted text for {path}: {text[:100]}...")
        except Exception as e:
            print(f"DEBUG VALIDATOR: Error extracting text from {path}: {e}")
            text_pages[path] = html  
    
    hints = json.dumps(patterns, indent=2)
    pages_condensed = "\n".join([f"PATH: {p}\nTEXT:\n{text_pages[p][:2000]}" for p in text_pages])  
    
    messages = [
        {"role":"system","content":SYSTEM},
        {"role":"user","content":(
            f"Domain: {domain}\n"
            f"URL map: {urls}\n"
            f"Signal hints: {hints}\n"
            f"Text content:\n{pages_condensed}\n"
            "Find the strongest signal and return ONLY the final JSON result."
        )}
    ]
    
    for i in range(step_limit):
        print(f"DEBUG VALIDATOR: Step {i+1}")
        try:
            out = llm.chat(messages).strip()
            print(f"DEBUG VALIDATOR: LLM response: {out[:200]}...")
        except Exception as e:
            print(f"DEBUG VALIDATOR: LLM error: {e}")
            messages.append({"role":"assistant","content":f"LLM error: {str(e)}"})
            continue
            
        clean = out.strip()
        if clean.startswith("```"):
            # Peel off common markdown fences before extracting JSON payload
            parts = [part.strip() for part in clean.split("```") if part.strip()]
            json_chunks = [chunk for chunk in parts if chunk.startswith("{") and "}" in chunk]
            if json_chunks:
                clean = json_chunks[0]

        def _iter_json_candidates(text: str):
            if text.startswith("{") and text.endswith("}"):
                yield text
            for match in re.finditer(r'"ok"\s*:', text):
                brace_start = text.rfind("{", 0, match.start())
                if brace_start == -1:
                    continue
                depth = 0
                in_string = False
                escape = False
                for idx in range(brace_start, len(text)):
                    ch = text[idx]
                    if in_string:
                        if escape:
                            escape = False
                        elif ch == "\\":
                            escape = True
                        elif ch == '"':
                            in_string = False
                        continue
                    else:
                        if ch == '"':
                            in_string = True
                        elif ch == "{":
                            depth += 1
                        elif ch == "}":
                            depth -= 1
                            if depth == 0:
                                yield text[brace_start:idx+1]
                                break

        tried = set()
        for candidate in _iter_json_candidates(clean):
            if candidate in tried:
                continue
            tried.add(candidate)
            if '"ok"' not in candidate:
                continue
            try:
                result = ValidateResult.model_validate_json(candidate)
                print(f"DEBUG VALIDATOR: Valid result: {result}")
                return result
            except ValidationError as e:
                print(f"DEBUG VALIDATOR: Validation error for candidate: {e}")

        messages.append({"role":"assistant","content":out})
        messages.append({"role":"user","content":"Please respond with ONLY the final JSON object matching the schema ({\"ok\": ..., \"signal_type\": ..., ...})."})
    
    print("DEBUG VALIDATOR: Step limit exceeded")
    return ValidateResult(ok=False, why=["step_limit_exceeded"])
