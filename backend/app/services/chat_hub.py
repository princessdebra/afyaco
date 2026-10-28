import uuid

from fastapi import WebSocket


class ChatHub:
    """In-memory WebSocket room registry, keyed by consultation_id.

    Single-process only — fine for this devserver's one-container deployment,
    but wouldn't fan out across multiple app replicas without a shared
    pub/sub (Redis, etc.) behind it. Documented limit, not hidden.
    """

    def __init__(self) -> None:
        self.rooms: dict[uuid.UUID, set[WebSocket]] = {}

    async def connect(self, consultation_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self.rooms.setdefault(consultation_id, set()).add(websocket)

    def disconnect(self, consultation_id: uuid.UUID, websocket: WebSocket) -> None:
        room = self.rooms.get(consultation_id)
        if room is not None:
            room.discard(websocket)
            if not room:
                self.rooms.pop(consultation_id, None)

    async def broadcast(self, consultation_id: uuid.UUID, payload: dict) -> None:
        for ws in list(self.rooms.get(consultation_id, ())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(consultation_id, ws)


hub = ChatHub()
