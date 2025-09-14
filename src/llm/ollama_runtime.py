import os
import json
import requests
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class OllamaConfig:
    model_id: str                      
    max_new_tokens: int = 400
    temperature: float = 0.1
    endpoint_url: Optional[str] = None # uses OLLAMA_BASE_URL
    device: str = "auto"               
    dtype: str = "float16"            

class OllamaChat:
    """
    Minimal chat client for talking ONLY to a local Ollama server.

    Env:
      OLLAMA_BASE_URL (optional) defaults to "http://localhost:11434"

    API:
      chat(messages) -> str
      messages: list of {"role": "system"|"user"|"assistant", "content": "..."}
    """
    def __init__(self, cfg: OllamaConfig):
        self.cfg = cfg
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

    def chat(self, messages: List[Dict[str, Any]]) -> str:
        url = f"{self.ollama_url}/api/chat"
        payload = {
            "model": self.cfg.model_id,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "options": {
                "temperature": self.cfg.temperature,
                "num_predict": self.cfg.max_new_tokens,
            },
            "stream": False,
        }
        r = requests.post(url, json=payload, timeout=600)
        r.raise_for_status()
        data = r.json()

        # Common Ollama response formats
        if isinstance(data, dict):
            if "message" in data and isinstance(data["message"], dict):
                return data["message"].get("content", "")
            if "messages" in data and isinstance(data["messages"], list) and data["messages"]:
                return data["messages"][-1].get("content", "")
            if "response" in data:
                return data.get("response", "")
        return json.dumps(data)
