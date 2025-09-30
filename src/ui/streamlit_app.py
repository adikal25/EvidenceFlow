"""Minimal Streamlit UI for Data Validation Agent

Run with:
    streamlit run src/ui/streamlit_app.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

import streamlit as st
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]


def find_results() -> Path:
    candidates = [ROOT / "results.jsonl", ROOT / "data" / "results.jsonl"]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def read_jsonl(path: Path) -> List[dict]:
    recs: List[dict] = []
    if not path.exists():
        return recs
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception:
                continue
    return recs


def main() -> None:
    st.set_page_config(
        page_title="Data Validation — Streamlit UI", layout="wide")
    st.title("Data Validation Agent — Results")

    results_path = find_results()
    st.sidebar.markdown("### Source")
    st.sidebar.write(str(results_path))

    records = read_jsonl(results_path)
    if not records:
        st.warning("No records found — falling back to sample data.")
        records = [
            {
                "domain": "http://localhost:8000",
                "company": "Test Business",
                "card": {"snippet": "We are excited to announce our new location opening"},
                "email": {"subject": "Congrats"},
            }
        ]

    domains = [r.get("domain") or "" for r in records]
    companies = [r.get("company") or "" for r in records]

    with st.sidebar:
        st.markdown("### Filters")
        domain_filter = st.text_input("Domain contains")
        company_filter = st.text_input("Company contains")
        limit = st.number_input(
            "Max records", min_value=1, max_value=1000, value=50)

    def match(r):
        if domain_filter and domain_filter.lower() not in (r.get("domain") or "").lower():
            return False
        if company_filter and company_filter.lower() not in (r.get("company") or "").lower():
            return False
        return True

    filtered = [r for r in records if match(r)][:limit]

    st.sidebar.markdown(
        f"**Total**: {len(records)}  |  **Shown**: {len(filtered)}")

    for r in filtered:
        st.subheader(f"{r.get('company') or ''} — {r.get('domain') or ''}")
        col1, col2 = st.columns([2, 3])
        with col1:
            st.markdown("**Card**")
            st.json(r.get("card") or {})
        with col2:
            st.markdown("**Email**")
            st.json(r.get("email") or {})
            # Gmail compose link (open compose window with subject & body prefilled)
            email = r.get("email") or {}
            subject = email.get("subject") if email.get(
                "subject") else f"Quick idea after {r.get('company') or ''} recent update"
            body = email.get("body") if email.get("body") else (
                f"Hi {r.get('company') or ''} — noticed: { (r.get('card') or {}).get('snippet') or '' }\n\nWe help teams act on this signal. Open to a 10-minute walkthrough?")

            def gmail_compose_url(subject: str, body: str, to: str = "") -> str:
                params = {
                    "view": "cm",
                    "fs": "1",
                    "to": to,
                    "su": subject,
                    "body": body,
                }
                qs = urllib.parse.urlencode(
                    params, quote_via=urllib.parse.quote)
                return f"https://mail.google.com/mail/?{qs}"

            url = gmail_compose_url(subject, body) # type: ignore
            # small Gmail icon SVG
            gmail_svg = """
<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><path d='M22 6.5v11a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-11'/><path d='M22 6.5 12 13 2 6.5'/></svg>
"""
            link_html = f"<a href=\"{url}\" target=\"_blank\" rel=\"noopener\" title=\"Open draft in Gmail\">{gmail_svg} Compose in Gmail</a>"
            st.markdown(link_html, unsafe_allow_html=True)
        st.markdown("---")


if __name__ == "__main__":
    main()
