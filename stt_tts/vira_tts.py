import logging
from dataclasses import dataclass
from typing import Optional

import requests

from config.settings import ViraSettings


logger = logging.getLogger(__name__)


@dataclass
class TTSResult:
    status: str
    filename: Optional[str] = None
    url: Optional[str] = None
    duration: Optional[float] = None


def synthesize_text(
    text: str,
    settings: ViraSettings,
    speaker: str = "female",
    speed: float = 1.0,
) -> TTSResult:
    token = settings.tts_token or settings.token
    if not token:
        logger.warning("Vira TTS token is missing; TTS call skipped.")
        return TTSResult(status="unauthorized")

    headers = {
        "gateway-token": token,
        "accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {"text": text, "speaker": speaker, "speed": speed, "timestamp": False}

    response = requests.post(
        settings.tts_url,
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    result = data.get("data", {})
    return TTSResult(
        status=data.get("status", "unknown"),
        filename=result.get("filename"),
        url=result.get("url"),
        duration=result.get("duration"),
    )
