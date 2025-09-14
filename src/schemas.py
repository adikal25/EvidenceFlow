from datetime import datetime
from typing import Optional, Literal, List, Dict
from pydantic import BaseModel, Field, HttpUrl


SignalType = Literal["expansion", "scheduler", "hiring"]


class AgentResult(BaseModel):
    ok: bool
    why: List[str] = []
    evidence_url: Optional[HttpUrl] = None
    snippet: Optional[str] = None
    published_at: Optional[datetime] = None
    confidence: float = 0.0
    extra: dict = {}

class EvidenceCard(BaseModel):
    signal_type: SignalType
    canonical_url: HttpUrl
    first_seen: datetime
    last_seen: datetime
    snippet: str = Field(max_length=320)
    screenshot_path: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    explain: str
    source_site: Optional[str] = None
    location_guess: Optional[str] = None


class ScrapeResult(BaseModel):
    ok: bool
    why: List[str] = []
    pages: Dict[str, str] = {}          # path -> html
    urls: Dict[str, HttpUrl] = {}       # path -> absolute url

class ValidateResult(BaseModel):
    ok: bool
    why: List[str] = []
    signal_type: Optional[str] = None                    # "expansion" | "scheduler" | "hiring"
    evidence_url: Optional[HttpUrl] = None
    snippet: Optional[str] = None
    published_at: Optional[datetime] = None
    confidence: float = 0.0