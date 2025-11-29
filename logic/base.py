from sessions.session import CallLeg, Session


class BaseScenario:
    """
    Base class for scenario handlers. Override only what you need.
    """

    def on_outbound_channel_created(self, session: Session) -> None:
        ...

    def on_inbound_channel_created(self, session: Session) -> None:
        ...

    def on_operator_channel_created(self, session: Session) -> None:
        ...

    def on_call_answered(self, session: Session, leg: CallLeg) -> None:
        ...

    def on_call_failed(self, session: Session, reason: str) -> None:
        ...

    def on_call_hangup(self, session: Session) -> None:
        ...

    def on_call_finished(self, session: Session) -> None:
        ...

    def on_playback_finished(self, session: Session, playback_id: str) -> None:
        ...
