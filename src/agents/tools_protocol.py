# Tools protocol
from typing import Dict, Any
from src.tools.web import fetch
from src.tools.web import extract_text, sentences
from src.tools.web import extract_date as get_meta_dates

TOOLS_SPEC = """
TOOLS USAGE:
Emit a single JSON object to call a tool:
{"tool": "fetch", "args": {"url": "https://..."}}
{"tool": "extract_text", "args": {"html": "<html>..."}}
{"tool": "find_matches", "args": {"text": "...", "patterns": ["..."], "max_sentences": 10}}
{"tool": "get_meta_dates", "args": {"html": "<html>..."}}
"""

def execute_tool(call: Dict[str, Any]) -> Dict[str, Any]:
    name = call.get("tool")
    args = call.get("args", {})
    try:
        if name == "fetch":
            html = fetch(args["url"]); return {"ok": True, "data": html}
        elif name == "extract_text":
            text = extract_text(args["html"]); return {"ok": True, "data": text}
        elif name == "find_matches":
            text = args["text"]; patterns = args.get("patterns", []); max_sent = int(args.get("max_sentences", 10))
            import re
            rx = re.compile("|".join(patterns), re.I) if patterns else None
            outs = []
            for s in sentences(text):
                if not s.strip(): continue
                if (rx and rx.search(s)) or (not rx): outs.append(s.strip())
                if len(outs) >= max_sent: break
            return {"ok": True, "data": outs}
        elif name == "get_meta_dates":
            dt = get_meta_dates(args["html"]); return {"ok": True, "data": (dt.isoformat() if dt else None)}
        else:
            return {"ok": False, "error": f"unknown tool '{name}'"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
