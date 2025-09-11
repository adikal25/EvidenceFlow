# graph orchestration
from src.llm.ollama_runtime import OllamaChat, OllamaConfig
from typing import Optional
from langgraph.graph import StateGraph, END
from pydantic import BaseModel
import yaml
from src.schemas import EvidenceCard,ScrapeResult, ValidateResult
from src.agents.evidence_card import build_card
from src.agents.outbound import draft_from_card, EmailDraft
from src.agents.scraper_agent import run_scraper_agent
from src.agents.validator_agent import run_validator_agent

CONFIDENCE_THRESHOLD = 0.6

class NodeState(BaseModel):
    domain: str
    company: Optional[str] = None
    scrape_result: Optional[ScrapeResult] = None
    validate_result: Optional[ValidateResult] = None
    card: Optional[EvidenceCard] = None
    email: Optional[EmailDraft] = None

def scrape_node(state: NodeState, llm: OllamaChat) -> NodeState:
    candidate = ["/","/locations","/book","/schedule","/appointments","/careers","/jobs","/blog","/news","/press"]
    state.scrape_result = run_scraper_agent(state.domain, candidate_paths=candidate, llm=llm, step_limit=5)
    return state

def validate_node(state: NodeState, llm: OllamaChat, patterns_cfg: dict) -> NodeState:
    if not state.scrape_result or not state.scrape_result.ok or not state.scrape_result.pages:
        return state
    PATS = {
        "expansion": patterns_cfg.get("expansion", ["grand opening","now open","new location"]),
        "scheduler": patterns_cfg.get("scheduler", ["calendly","acuity","book","schedule","appointment"]),
        "hiring":    patterns_cfg.get("hiring",    ["hiring","role","apply","careers","jobs"]),
    }
    vr = run_validator_agent(state.domain, state.scrape_result.pages, state.scrape_result.urls, PATS, llm=llm, step_limit=4)
    state.validate_result = vr
    if vr.ok and vr.evidence_url and vr.snippet:
        state.card = build_card(vr.signal_type, str(vr.evidence_url), vr.snippet, vr.published_at)
    return state

def outbound_node(state: NodeState, llm: OllamaChat) -> NodeState:
    if state.card and (state.card.confidence >= CONFIDENCE_THRESHOLD):
        state.email = draft_from_card(
            llm,
            company=state.company or state.domain.split(".")[0].title(),
            domain=state.domain,
            signal_type=state.card.signal_type,
            url=str(state.card.canonical_url),
            snippet=state.card.snippet,
            confidence=state.card.confidence
        )
    return state

def _build_chat(cfg_block: dict) -> OllamaChat:
    return OllamaChat(OllamaConfig(
        model_id      = cfg_block.get("model_id", "phi3.5"),
        max_new_tokens= cfg_block.get("max_new_tokens", 240),
        temperature   = cfg_block.get("temperature", 0.1),
    ))

def make_graph(config_path="configs/config.yml", vertical_config: dict | None = None):
    cfg = yaml.safe_load(open(config_path))
    llm_root = cfg.get("llm", {})
    llm_val = _build_chat(llm_root.get("validator", {}))
    llm_out = _build_chat(llm_root.get("outbound", {}))
    patterns = (vertical_config or {}).get("phrases", {})

    g = StateGraph(NodeState)
    g.add_node("scrape_node",        lambda s: scrape_node(s, llm=llm_val))
    g.add_node("validate_node",      lambda s: validate_node(s, llm=llm_val, patterns_cfg=patterns))
    g.add_node("outbound_gate", lambda s: outbound_node(s, llm=llm_out))
    g.set_entry_point("scrape_node")
    g.add_edge("scrape_node","validate_node")
    g.add_edge("validate_node","outbound_gate")
    g.add_edge("outbound_gate", END)
    return g.compile()
