# src/tools/web.py
from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from readability import Document
import dateparser

# Public API
__all__ = ["fetch", "extract_text", "sentences", "extract_date"]

# ---- HTTP fetching ----

DEFAULT_HEADERS = {
    "User-Agent": (
        "SignalProto-Agent/1.0 (+https://example.local) "
        "Mozilla/5.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.7",
    "Connection": "close",
}

def _make_session() -> requests.Session:
    s = requests.Session()
    # Setting a small connection pool; this is a CLI tool.
    adapter = requests.adapters.HTTPAdapter( # type: ignore
        pool_connections=4, pool_maxsize=4, max_retries=3
    )
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

def fetch(
    url: str,
    *,
    timeout: int = 20,
    headers: Optional[Dict[str, str]] = None,
    allow_redirects: bool = True,
) -> str:
    """
    Fetch the URL and return response text (decoded HTML).
    Raises requests.HTTPError on non-2xx.
    """
    session = _make_session()
    h = dict(DEFAULT_HEADERS)
    if headers:
        h.update(headers)

    resp = session.get(
        url,
        headers=h,
        timeout=timeout,
        allow_redirects=allow_redirects,
    )
    # Raise for HTTP errors
    resp.raise_for_status()

    # Use requests' decoding (charset-normalizer) if provided by server,
    # else fallback to apparent encoding for a best-effort decode.
    if not resp.encoding:
        resp.encoding = resp.apparent_encoding

    return resp.text


def extract_text(html: str) -> str:
    try:
        doc = Document(html)
        content_html = doc.summary(html_partial=True)
    except Exception:
        content_html = html
    soup = BeautifulSoup(content_html, "lxml")
    text = soup.get_text(" ", strip=True)
    return " ".join(text.split())

def sentences(text: str):
    return re.split(r"(?<=[.!?])\s+", text)

def extract_date(html: str):
    soup = BeautifulSoup(html, "lxml")
    for sel in [
        ("meta", {"property": "article:published_time"}),
        ("meta", {"name": "date"}),
        ("time", {}),
    ]:
        el = soup.find(*sel)
        if el:
            val = el.get("content") or el.get_text(strip=True)
            dt = dateparser.parse(val)
            if dt:
                return dt
    m = re.search(
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}",
        soup.get_text(" ", strip=True),
    )
    if m:
        dt = dateparser.parse(m.group(0))
        if dt:
            return dt
    return None
