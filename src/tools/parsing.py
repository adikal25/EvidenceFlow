# parsing implementation
import re
from bs4 import BeautifulSoup
from readability import Document
import dateparser

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
    for sel in [("meta", {"property":"article:published_time"}), ("meta", {"name":"date"}), ("time", {})]:
        el = soup.find(*sel)
        if el:
            val = el.get("content") or el.get_text(strip=True)
            dt = dateparser.parse(val)
            if dt: return dt
    m = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}", soup.get_text(" ", strip=True))
    if m:
        dt = dateparser.parse(m.group(0))
        if dt: return dt
    return None
