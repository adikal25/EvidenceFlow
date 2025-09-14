from pydantic import ValidationError
from src.llm.ollama_runtime import OllamaChat, OllamaConfig

from src.agents.tools_protocol import TOOLS_SPEC, execute_tool
import json, re
from typing import List
from src.schemas import ScrapeResult

SYSTEM = f"""
You are a data collection assistant. You MUST use the provided tools to fetch web pages.

CRITICAL: You must call the tools using the exact JSON format shown below. Do NOT write any code, JavaScript, or explanations.

Available tools:
{TOOLS_SPEC}

Return FINAL JSON matching this schema exactly:
{ScrapeResult.model_json_schema()}

EXAMPLES OF CORRECT TOOL USAGE:
1. To fetch a page: {{"tool": "fetch", "args": {{"url": "https://example.com/"}}}}
2. To extract text: {{"tool": "extract_text", "args": {{"html": "<html>...</html>"}}}}

Instructions:
1. Call fetch tool for each path you want to try (ONE AT A TIME)
2. After getting responses, return the final JSON with pages and urls populated
3. The pages should contain the HTML content you fetched
4. The urls should contain the actual URLs you accessed
5. If you cannot access any pages, return ok=false with a reason
6. Always end with FINAL JSON only

DO NOT write code, JavaScript, or explanations. Just call the tools and return JSON.
"""

def _try_json(line: str):
    try: 
        return json.loads(line.strip())
    except: 
        return None

def run_scraper_agent(domain: str, candidate_paths: List[str], *, llm: OllamaChat, step_limit=5) -> ScrapeResult:

    messages = [
        {"role":"system","content":SYSTEM},
        {"role":"user","content":(
            f"Collect data from: {domain}\n"
            f"Try these paths: {candidate_paths}\n"
            "Call the fetch tool for each path, then return the results as JSON with pages and urls populated."
        )}
    ]

    print(f"DEBUG: Starting scraper for domain: {domain}")
    
    # Store fetched data
    pages = {}
    urls = {}
    
    for i in range(step_limit):
        try:
            print(f"DEBUG: Step {i+1}, calling LLM...")
            out = llm.chat(messages).strip()
            print(f"DEBUG: LLM response length: {len(out)}")
            print(f"DEBUG: LLM response: {out[:200]}...")
        except Exception as e:
            print(f"DEBUG: LLM error: {str(e)}")
            messages.append({"role":"assistant","content":f"LLM error: {str(e)}"})
            continue
        
        # Handle empty response
        if not out:
            print("DEBUG: Empty response from LLM")
            messages.append({"role":"assistant","content":"Empty response"})
            continue
            
        try:
            lines = out.splitlines()
            if not lines:
                print("DEBUG: No lines in response")
                messages.append({"role":"assistant","content":"No lines in response"})
                continue
                
            # Look for tool calls in any line
            tool_found = False
            for line in lines:
                # Handle multiple tool calls separated by semicolons
                if ';' in line:
                    tool_calls = line.split(';')
                    for tool_call in tool_calls:
                        maybe = _try_json(tool_call.strip())
                        if isinstance(maybe, dict) and "tool" in maybe:
                            print(f"DEBUG: Tool call detected: {maybe}")
                            result = execute_tool(maybe)
                            print(f"DEBUG: Tool result: {result}")
                            
                            # Store the result
                            if result.get("ok") and "data" in result:
                                if maybe["tool"] == "fetch":
                                    url = maybe["args"]["url"]
                                    path = url.replace(domain, "")
                                    if not path:
                                        path = "/"
                                    pages[path] = result["data"]
                                    urls[path] = url
                                    print(f"DEBUG: Stored page for path {path}")
                            
                            messages.append({"role":"assistant","content": json.dumps(maybe)})
                            messages.append({"role":"tool","content":json.dumps({"tool_result": result})})
                            tool_found = True
                else:
                    maybe = _try_json(line)
                    if isinstance(maybe, dict) and "tool" in maybe:
                        print(f"DEBUG: Tool call detected: {maybe}")
                        result = execute_tool(maybe)
                        print(f"DEBUG: Tool result: {result}")
                        
                        # Store the result
                        if result.get("ok") and "data" in result:
                            if maybe["tool"] == "fetch":
                                url = maybe["args"]["url"]
                                path = url.replace(domain, "")
                                if not path:
                                    path = "/"
                                pages[path] = result["data"]
                                urls[path] = url
                                print(f"DEBUG: Stored page for path {path}")
                        
                        messages.append({"role":"assistant","content": json.dumps(maybe)})
                        messages.append({"role":"tool","content":json.dumps({"tool_result": result})})
                        tool_found = True
                        break
                    
            if tool_found:
                continue
                
            # Check for final JSON result
            m = re.search(r"\{.*\}\s*$", out, flags=re.S)
            if m:
                try:
                    print(f"DEBUG: Found JSON, validating...")
                    result = ScrapeResult.model_validate_json(m.group(0))
                    print(f"DEBUG: Valid result: {result}")
                    return result
                except ValidationError as e:
                    print(f"DEBUG: Validation error: {e}")
                    messages.append({"role":"assistant","content":out});
                    continue
                    
            messages.append({"role":"assistant", "content": out})
        except Exception as e:
            print(f"DEBUG: Processing error: {str(e)}")
            messages.append({"role":"assistant","content":f"Processing error: {str(e)}"})
            continue
            
    # If we have collected some data, return it
    print(f"DEBUG: Final check - pages collected: {len(pages)}")
    print(f"DEBUG: Pages: {list(pages.keys())}")
    print(f"DEBUG: URLs: {list(urls.keys())}")
    
    if pages:
        print(f"DEBUG: Returning collected data: {len(pages)} pages")
        return ScrapeResult(ok=True, why=[], pages=pages, urls=urls)
    else:
        print("DEBUG: No data collected")
        return ScrapeResult(ok=False, why=["no_data_collected"])