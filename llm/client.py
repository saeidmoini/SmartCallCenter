import logging
from typing import Any, Dict, List, Optional

import requests

from config.settings import GapGPTSettings


logger = logging.getLogger(__name__)


class GapGPTClient:
    """
    Minimal wrapper around GapGPT (OpenAI-compatible) chat completions.
    """

    def __init__(self, settings: GapGPTSettings):
        self.base_url = settings.base_url.rstrip("/")
        self.api_key = settings.api_key
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        self.session.headers.update({"Content-Type": "application/json"})

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not self.api_key:
            logger.warning("GapGPT API key not provided; returning empty response.")
            return ""

        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        response = self.session.post(url, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
