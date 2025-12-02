from sessions.session import CallLeg, Session


class BaseScenario:
    """
    Base class for scenario handlers. Override only what you need.
    """

    async def on_outbound_channel_created(self, session: Session) -> None:
        ...

    async def on_inbound_channel_created(self, session: Session) -> None:
        ...

    async def on_operator_channel_created(self, session: Session) -> None:
        ...

    async def on_call_answered(self, session: Session, leg: CallLeg) -> None:
        ...

    async def on_call_failed(self, session: Session, reason: str) -> None:
        ...

    async def on_call_hangup(self, session: Session) -> None:
        ...

    async def on_call_finished(self, session: Session) -> None:
        ...

    async def on_playback_finished(self, session: Session, playback_id: str) -> None:
        ...

    async def on_recording_finished(self, session: Session, recording_name: str) -> None:
        ...

    async def on_recording_failed(self, session: Session, recording_name: str, cause: str) -> None:
        ...
