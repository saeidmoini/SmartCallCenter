import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from config.settings import GapGPTSettings


logger = logging.getLogger(__name__)


class GapGPTClient:
    """
    Minimal async wrapper around GapGPT (OpenAI-compatible) chat completions.
    """

    def __init__(
        self,
        settings: GapGPTSettings,
        timeout: float = 20.0,
        max_connections: int = 100,
        semaphore: Optional[asyncio.Semaphore] = None,
    ):
        self.base_url = settings.base_url.rstrip("/")
        self.api_key = settings.api_key
        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_connections,
        )
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
            limits=limits,
        )
        self.timeout = timeout
        self.semaphore = semaphore or asyncio.Semaphore(10)

    async def close(self) -> None:
        await self.client.aclose()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not self.api_key:
            logger.warning("GapGPT API key not provided; returning empty response.")
            return ""

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        async with self.semaphore:
            response = await self.client.post(
                "/chat/completions",
                json=payload,
                timeout=self.timeout,
            )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
