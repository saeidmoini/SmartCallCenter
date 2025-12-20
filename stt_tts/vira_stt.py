import asyncio
import logging
from dataclasses import dataclass
import subprocess
import tempfile
from pathlib import Path
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


class ViraSTTClient:
    """
    Async Vira STT wrapper with concurrency control.
    """

    def __init__(
        self,
        settings: ViraSettings,
        timeout: float = 30.0,
        max_connections: int = 100,
        semaphore: Optional[asyncio.Semaphore] = None,
    ):
        self.settings = settings
        self.timeout = timeout
        self.semaphore = semaphore or asyncio.Semaphore(10)
        if not settings.verify_ssl:
            try:
                import urllib3

                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass

    async def close(self) -> None:
        return

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        language_model: str = "default",
        hotwords: Optional[list[str]] = None,
    ) -> STTResult:
        audio_bytes = await asyncio.to_thread(self._enhance_audio, audio_bytes)
        token = self.settings.stt_token
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
        data_list = [
            ("model", language_model),
            ("srt", "false"),
            ("inverseNormalizer", "false"),
            ("timestamp", "false"),
            ("spokenPunctuation", "false"),
            ("punctuation", "false"),
            ("numSpeakers", "0"),
            ("diarize", "false"),
        ]
        if hotwords:
            for word in hotwords:
                data_list.append(("hotwords[]", word))

        async with self.semaphore:
            response = await asyncio.to_thread(
                self._post_sync,
                headers,
                data_list,
                audio_bytes,
            )
        if response.status_code >= 400:
            try:
                logger.error(
                    "Vira STT error %s: %s", response.status_code, response.text
                )
            except Exception:
                logger.error("Vira STT error %s (failed to read body)", response.status_code)
        response.raise_for_status()
        payload = response.json()
        data_section = payload.get("data", {}) or {}
        nested_data = data_section.get("data", {}) or {}
        ai_response = nested_data.get("aiResponse", {}) or {}
        ai_result = ai_response.get("result", {}) or {}

        text = (
            data_section.get("text")
            or nested_data.get("text")
            or ai_result.get("text")
            or ""
        )
        status = (
            data_section.get("status")
            or payload.get("status")
            or ai_response.get("status")
            or "unknown"
        )
        request_id = (
            data_section.get("requestId")
            or nested_data.get("requestId")
            or ai_response.get("requestId")
        )
        trace_id = (
            data_section.get("traceId")
            or nested_data.get("traceId")
            or ai_response.get("meta", {}).get("traceId")
        )

        if not text:
            logger.warning("Vira STT returned empty text. status=%s payload=%s", status, payload)

        return STTResult(status=status, text=text, request_id=request_id, trace_id=trace_id)

    def _enhance_audio(self, audio_bytes: bytes) -> bytes:
        """
        Light denoise/normalize without trimming the start of the call.
        Requires ffmpeg; on failure returns original audio.
        """
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                inp = Path(tmpdir) / "in.wav"
                outp = Path(tmpdir) / "out.wav"
                inp.write_bytes(audio_bytes)
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(inp),
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-af",
                    "highpass=f=120,lowpass=f=3800,afftdn=nf=-25,"
                    "loudnorm=I=-19:TP=-2:LRA=8",
                    str(outp),
                ]
                result = subprocess.run(cmd, capture_output=True, check=False)
                if result.returncode != 0:
                    logger.debug("ffmpeg enhance failed; using raw audio. stderr=%s", result.stderr.decode(errors="ignore"))
                    return audio_bytes
                return outp.read_bytes()
        except FileNotFoundError:
            logger.debug("ffmpeg not found; using raw audio")
        except Exception as exc:
            logger.debug("Audio enhancement failed; using raw audio: %s", exc)
        return audio_bytes

    def _post_sync(self, headers: dict, data_list: list, audio_bytes: bytes) -> requests.Response:
        files = {"audio": ("audio.wav", audio_bytes, "audio/wav")}
        return requests.post(
            self.settings.stt_url,
            headers=headers,
            data=data_list,
            files=files,
            timeout=self.timeout,
            verify=self.settings.verify_ssl,
        )
