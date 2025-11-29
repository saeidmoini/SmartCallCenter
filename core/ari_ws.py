import json
import logging
import threading
from typing import Callable, Optional

import websocket

from config.settings import AriSettings


logger = logging.getLogger(__name__)


class AriWebSocketClient:
    """
    Subscribes to ARI events and forwards them to the provided handler.
    """

    def __init__(self, settings: AriSettings, event_handler: Callable[[dict], None]):
        self.settings = settings
        self.event_handler = event_handler
        self.ws: Optional[websocket.WebSocketApp] = None
        self.thread: Optional[threading.Thread] = None

    def _build_url(self) -> str:
        return (
            f"{self.settings.ws_url}"
            f"?app={self.settings.app_name}"
            f"&api_key={self.settings.username}:{self.settings.password}"
        )

    def _on_message(self, _ws: websocket.WebSocketApp, message: str) -> None:
        try:
            event = json.loads(message)
            logger.debug("Received ARI event: %s", event.get("type"))
            self.event_handler(event)
        except json.JSONDecodeError:
            logger.error("Failed to decode ARI event: %s", message)
        except Exception as exc:
            logger.exception("Unexpected error handling ARI event: %s", exc)

    def _on_error(self, _ws: websocket.WebSocketApp, error: Exception) -> None:
        logger.error("WebSocket error: %s", error)

    def _on_close(
        self,
        _ws: websocket.WebSocketApp,
        close_status_code: int,
        close_msg: str,
    ) -> None:
        logger.warning(
            "WebSocket closed code=%s message=%s", close_status_code, close_msg
        )

    def _on_open(self, _ws: websocket.WebSocketApp) -> None:
        logger.info("Connected to ARI WebSocket")

    def start(self) -> None:
        url = self._build_url()
        logger.info("Connecting to ARI WebSocket at %s", self.settings.ws_url)
        self.ws = websocket.WebSocketApp(
            url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
        )
        self.thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.ws:
            logger.info("Closing ARI WebSocket")
            self.ws.close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
