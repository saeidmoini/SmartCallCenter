import logging
from dataclasses import dataclass
from typing import Optional

import requests

from config.settings import ViraSettings


logger = logging.getLogger(__name__)


@dataclass
class STTResult:
    status: str
    text: str
    request_id: Optional[str] = None
    trace_id: Optional[str] = None


def transcribe_audio(
    audio_bytes: bytes,
    settings: ViraSettings,
    language_model: str = "default",
) -> STTResult:
    token = settings.stt_token or settings.token
    if not token:
        logger.warning("Vira STT token is missing; STT call skipped.")
        return STTResult(status="unauthorized", text="")

    headers = {
        "gateway-token": token,
        "accept": "application/json",
    }
    files = {
        "audio": ("audio.wav", audio_bytes, "audio/wav"),
    }
    data = {
        "model": language_model,
        "srt": "false",
        "inverseNormalizer": "false",
        "timestamp": "false",
        "spokenPunctuation": "true",
        "punctuation": "true",
        "numSpeakers": "1",
        "diarize": "false",
    }

    response = requests.post(
        settings.stt_url,
        headers=headers,
        data=data,
        files=files,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    text = payload.get("data", {}).get("text", "")
    status = payload.get("status", "unknown")
    request_id = payload.get("data", {}).get("requestId")
    trace_id = payload.get("data", {}).get("traceId")
    return STTResult(status=status, text=text, request_id=request_id, trace_id=trace_id)
