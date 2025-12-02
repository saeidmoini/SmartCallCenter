import asyncio
import logging
from collections import deque
from datetime import date, datetime, timedelta
from typing import Deque, List, Optional

from config.settings import Settings
from core.ari_client import AriClient
from sessions.session_manager import SessionManager


logger = logging.getLogger(__name__)


class Dialer:
    """
    Outbound dialer that enforces concurrency and rate limits.
    """

    def __init__(
        self,
        settings: Settings,
        ari_client: AriClient,
        session_manager: SessionManager,
    ):
        self.settings = settings
        self.ari_client = ari_client
        self.session_manager = session_manager
        self.contacts: Deque[str] = deque(settings.dialer.static_contacts)
        self.attempt_timestamps: Deque[datetime] = deque()
        self.daily_counter = 0
        self.daily_marker: date = date.today()
        self._running = False
        self.lock = asyncio.Lock()

    async def run(self, stop_event: asyncio.Event) -> None:
        if self._running:
            return
        self._running = True
        logger.info("Dialer started with %d queued contacts", len(self.contacts))
        try:
            while not stop_event.is_set() and self._running:
                self._reset_daily_if_needed()
                if not self._within_call_window():
                    await asyncio.sleep(30)
                    continue
                if not await self._can_start_call():
                    await asyncio.sleep(1)
                    continue
                contact = await self._next_contact()
                if not contact:
                    await asyncio.sleep(5)
                    continue
                await self._originate(contact)
                await asyncio.sleep(0.2)
        finally:
            self._running = False
            logger.info("Dialer stopped")

    async def stop(self) -> None:
        self._running = False

    async def add_contacts(self, numbers: List[str]) -> None:
        async with self.lock:
            for number in numbers:
                clean = number.strip()
                if clean:
                    self.contacts.append(clean)
        logger.info("Queued %d new contacts", len(numbers))

    async def on_session_completed(self, session_id: str) -> None:
        logger.debug("Session %s completed; dialer notified", session_id)

    def _within_call_window(self) -> bool:
        now = datetime.now().time()
        start = self.settings.dialer.call_window_start
        end = self.settings.dialer.call_window_end
        if start <= now <= end:
            return True
        logger.debug("Outside call window (%s - %s)", start, end)
        return False

    def _reset_daily_if_needed(self) -> None:
        today = date.today()
        if today != self.daily_marker:
            logger.info("Resetting daily counters")
            self.daily_counter = 0
            self.daily_marker = today
            self.attempt_timestamps.clear()

    async def _can_start_call(self) -> bool:
        current_sessions = await self.session_manager.active_sessions_count()
        if current_sessions >= self.settings.dialer.max_concurrent_calls:
            return False

        self._prune_attempts()
        if len(self.attempt_timestamps) >= self.settings.dialer.max_calls_per_minute:
            return False

        if self.daily_counter >= self.settings.dialer.max_calls_per_day:
            return False

        return True

    def _prune_attempts(self) -> None:
        cutoff = datetime.utcnow() - timedelta(minutes=1)
        while self.attempt_timestamps and self.attempt_timestamps[0] < cutoff:
            self.attempt_timestamps.popleft()

    async def _next_contact(self) -> Optional[str]:
        async with self.lock:
            if not self.contacts:
                return None
            return self.contacts.popleft()

    async def _originate(self, contact: str) -> None:
        try:
            session = await self.session_manager.create_outbound_session(contact_number=contact)
            endpoint = self._build_endpoint(contact)
            app_args = f"outbound,{session.session_id}"
            await self.ari_client.originate_call(
                endpoint=endpoint,
                app_args=app_args,
                caller_id=self.settings.dialer.default_caller_id,
                timeout=self.settings.dialer.origination_timeout,
            )
            self._record_attempt()
            logger.info(
                "Origination requested for %s (session %s)", contact, session.session_id
            )
        except Exception as exc:
            logger.exception("Failed to originate call to %s: %s", contact, exc)

    def _record_attempt(self) -> None:
        self.attempt_timestamps.append(datetime.utcnow())
        self.daily_counter += 1

    def _build_endpoint(self, contact: str) -> str:
        trunk = self.settings.dialer.outbound_trunk
        return f"PJSIP/{contact}@{trunk}"
