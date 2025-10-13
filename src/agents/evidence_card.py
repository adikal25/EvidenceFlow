# build_card
from datetime import datetime, timezone
from src.scoring import freshness_weight, confidence
from src.schemas import EvidenceCard

def build_card(signal_type, evidence_url, snippet, published_at, screenshot_path=None):
    w = freshness_weight(published_at)
    conf, why = confidence(signal_type, snippet, w)
    now = datetime.now(timezone.utc)
    if published_at and not published_at.tzinfo:
        published_at = published_at.replace(tzinfo=timezone.utc)
    first_seen = published_at or now
    return EvidenceCard(
        signal_type=signal_type,
        canonical_url=evidence_url,
        first_seen=now,
        last_seen=now,
        snippet=snippet[:250],
        screenshot_path=screenshot_path,
        confidence=conf,
        explain=f"{why}; freshness= {round(w,2)}",
    )
