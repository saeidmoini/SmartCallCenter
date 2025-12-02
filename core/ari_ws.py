import asyncio
import json
import logging
from typing import Awaitable, Callable, Optional

import websockets
from websockets import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from config.settings import AriSettings


logger = logging.getLogger(__name__)


class AriWebSocketClient:
    """
    Subscribes to ARI events and forwards them to the provided async handler.
    """

    def __init__(
        self,
        settings: AriSettings,
        event_handler: Callable[[dict], Awaitable[None]],
    ):
        self.settings = settings
        self.event_handler = event_handler
        self._ws: Optional[WebSocketClientProtocol] = None
        self._stop_event = asyncio.Event()

    def _build_url(self) -> str:
        return (
            f"{self.settings.ws_url}"
            f"?app={self.settings.app_name}"
            f"&api_key={self.settings.username}:{self.settings.password}"
        )

    async def run(self) -> None:
        """
        Maintain the WebSocket connection and fan out events as tasks.
        """
        while not self._stop_event.is_set():
            url = self._build_url()
            try:
                logger.info("Connecting to ARI WebSocket at %s", self.settings.ws_url)
                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=20,
                    max_queue=None,
                ) as ws:
                    self._ws = ws
                    logger.info("Connected to ARI WebSocket")
                    await self._consume(ws)
            except (ConnectionClosedError, ConnectionClosedOK) as exc:
                if self._stop_event.is_set():
                    break
                logger.warning("ARI WebSocket closed: %s; reconnecting...", exc)
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                logger.exception("WebSocket error; reconnecting: %s", exc)
            self._ws = None
            if not self._stop_event.is_set():
                await asyncio.sleep(1)
        logger.info("ARI WebSocket listener stopped")

    async def _consume(self, ws: WebSocketClientProtocol) -> None:
        async for message in ws:
            if self._stop_event.is_set():
                break
            await self._handle_message(message)

    async def _handle_message(self, message: str) -> None:
        try:
            event = json.loads(message)
            logger.debug("Received ARI event: %s", event.get("type"))
            task = asyncio.create_task(self.event_handler(event))
            task.add_done_callback(self._log_task_exception)
        except json.JSONDecodeError:
            logger.error("Failed to decode ARI event: %s", message)
        except Exception as exc:
            logger.exception("Unexpected error handling ARI event: %s", exc)

    async def stop(self) -> None:
        self._stop_event.set()
        if self._ws:
            await self._ws.close()

    @staticmethod
    def _log_task_exception(task: asyncio.Task) -> None:
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return
        if exc:
            logger.exception("Unhandled exception in ARI event task: %s", exc)
