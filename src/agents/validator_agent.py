import json, re
from typing import Dict, List
from pydantic import ValidationError
from src.llm.ollama_runtime import OllamaChat
from src.schemas import ValidateResult
from src.tools.parsing import extract_text

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
    
    # Extract text from HTML pages
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
            
        # Look for JSON in the response
        json_match = re.search(r'\{[^{}]*"ok"[^{}]*\}', out, re.DOTALL)
        if json_match:
            try:
                result = ValidateResult.model_validate_json(json_match.group(0))
                print(f"DEBUG VALIDATOR: Valid result: {result}")
                return result
            except ValidationError as e:
                print(f"DEBUG VALIDATOR: Validation error: {e}")
                messages.append({"role":"assistant","content":out}); 
                continue
        
        m = re.search(r"\{.*\}\s*$", out, flags=re.S)
        if m:
            try:
                result = ValidateResult.model_validate_json(m.group(0))
                print(f"DEBUG VALIDATOR: Valid result: {result}")
                return result
            except ValidationError as e:
                print(f"DEBUG VALIDATOR: Validation error: {e}")
                messages.append({"role":"assistant","content":out}); 
                continue
                
        messages.append({"role":"assistant","content":out})
    
    print("DEBUG VALIDATOR: Step limit exceeded")
    return ValidateResult(ok=False, why=["step_limit_exceeded"])
