# scoring heurostics on how good the agent is
import re
from datetime import datetime,timezone
EXPLICIT = re.compile(r"(grand\s*opening|now\s*open|new\s*location|opened\s*(our\s*)?(second|third))", re.I)
ADDRLIKE = re.compile(r"\d{2,5}\s+\w+", re.I)
def freshness_weight(published_at, weekly_decay=0.85, floor=0.3):
    """Calculate freshness weight based on publication date with weekly decay."""
    if not published_at: 
        return 0.9
    n = datetime.now(timezone.utc)
    weeks = max(0, (n - published_at).days / 7)
    w = (weekly_decay ** weeks) if weeks else 1.0
    return max(floor, w)


def confidence(signal_type: str, snippet: str, w: float):
    """Calculate confidence score based on signal type, snippet content, and weight."""
    base = 0.4; why=[]
    if EXPLICIT.search(snippet): 
        base+=0.3
        why.append("explicit_phrase")
    if ADDRLIKE.search(snippet):
        base+=0.1
        why.append("address_like")
    if signal_type == "scheduler":
        base += 0.1
        why.append("vendor_hint")
    score = min(1.0, base*w)
    return round(score,3), ",".join(why) or "generic"
