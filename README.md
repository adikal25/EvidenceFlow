
# Overview

This project is a **prototype AI Agent Stack** for detecting **business activity signals** on SMB websites. It focuses on three high‑value triggers:

- **Expansion** → “Grand Opening”, “New Location”  
- **Hiring** → careers/job postings  
- **Scheduler** → Calendly / Acuity / “Book Appointment”  

Each signal is wrapped into an **Evidence Card**, then passed to an **Outbound Agent** that drafts a personalized email.

**Goal.** Help sales and marketing teams discover timely triggers that indicate a business is actively growing and worth contacting now.

# Features

- **Multi‑agent pipeline** with LangGraph orchestration  
- **Modular design** with Pydantic schemas  
- **Local inference with Ollama** (no API costs)  
- **Scoring heuristics**
  - Regex‑based intent detection
  - Confidence weighting with **freshness decay**
- **Automatic email draft generation** tied to detected signals  
- **Configurable via YAML** (`configs/config.yml`)  
- **Optional front‑end**: `demo.html` for visualizing cards & emails

# Tech Stack

- **Agents:** LangGraph (StateGraph orchestration)  
- **LLM Runtime:** Ollama (local models like `phi3.5`, `llama3.1`)  
- **Schemas:** Pydantic  
- **Scraping:** Requests + BeautifulSoup4 (via `tools/`)  
- **Validation:** Regex patterns + freshness‑decay scoring  
- **Embeddings / Reranker (optional):** `BAAI/bge-m3`, `bge-reranker`  
- **UI (optional):** HTML demo page (`demo.html`)

# Setup

## 1. Clone repo

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

## 2. Install dependencies

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Install & run Ollama

- Download **Ollama**  
- Pull a model (e.g., **Phi‑3.5 Mini**) you can plug and play with the models:

```bash
ollama pull phi3.5
```

Ensure server is running locally at <http://localhost:11434>.

## 4. Configure YAML

Update `configs/config.yml` as needed:

```yaml
gate:
  min_confidence: 0.6

confidence:
  weekly_decay: 0.85
  floor: 0.3

llm:
  validator:
    model_id: phi3.5
    backend: ollama
    max_new_tokens: 200
    temperature: 0.05
  outbound:
    model_id: phi3.5
    backend: ollama
    max_new_tokens: 300
    temperature: 0.25
```

## 5. Run pipeline

```bash
python -m src.app --csv data/test_sites.csv --vertical dentists --out data/results.jsonl
```

# Testing

Create a test HTML page with strong signals:

```html
<h1>Grand Opening! Now Open our new clinic in Dallas</h1>
<p>Book an appointment today!</p>
<p>We are hiring staff for our new team.</p>
```

Serve it locally:

```bash
python -m http.server 8000
```

Add to `data/test_sites.csv`:

```csv
domain,company
localhost:8000,Test Business
```

Run the pipeline again—expect a populated **Evidence Card** and **email draft**.

# Output Example

```json
{
  "domain": "localhost:8000",
  "company": "Test Business",
  "card": {
    "signal_type": "expansion",
    "canonical_url": "http://localhost:8000/",
    "snippet": "Grand Opening! Now Open our new clinic in Dallas",
    "confidence": 0.72,
    "explain": "explicit_phrase; freshness=0.92"
  },
  "email": {
    "subject": "Congrats on your new Dallas clinic",
    "body": "Hi Test Business — noticed your Dallas opening.\n\nMany teams use AI-assisted workflows to route leads in real time and convert faster.\n\nWould a 10-minute walkthrough next week be useful?",
    "call_to_action": "Open to a quick walkthrough?"
  }
}
```

# Architecture Notes

- **LangGraph** coordinates a StateGraph of tools/agents that:
  1. **Fetch** and **parse** site content,
  2. **Detect** signals via regex/semantic cues,
  3. **Score** with freshness decay,
  4. **Assemble** Evidence Cards,
  5. **Draft** outbound emails conditioned on the detected signal(s).
- **Pydantic** enforces strict schemas for Evidence Cards and email payloads.
- **Ollama** enables local inference for validator and outbound generation, minimizing cost and maximizing privacy.

# Future Improvements

- **Semantic scoring** with FAISS + reranker  
- **Streamlit dashboard** to visualize Evidence Cards & drafts  
- **CRM/marketing integrations** for automated workflows

# License

MIT — feel free to use, extend, and improve.

# Appendix

## Example Directory Layout

```text
.
├── configs/
│   └── config.yml
├── data/
│   ├── test_sites.csv
│   └── results.jsonl
├── demo.html
├── requirements.txt
├── src/
│   ├── app.py
│   ├── agents/
│   ├── tools/
│   └── schemas/
└── README.Rmd
```

## Evidence Card (Pydantic) — illustrative schema

```python
from pydantic import BaseModel, HttpUrl
from typing import Literal, Optional

class EvidenceCard(BaseModel):
    signal_type: Literal["expansion", "hiring", "scheduler"]
    canonical_url: Optional[HttpUrl] = None
    snippet: str
    confidence: float
    explain: str
```

## CLI Usage

```bash
python -m src.app \\
  --csv data/test_sites.csv \\
  --vertical dentists \\
  --out data/results.jsonl
```
