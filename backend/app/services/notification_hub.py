import uuid

from fastapi import WebSocket


class NotificationHub:
    """Same pattern as ChatHub, but rooms are keyed by user_id instead of
    consultation_id — one user may have several tabs/devices open, all get
    the push. Same single-process limitation (see ChatHub).
    """

    def __init__(self) -> None:
        self.rooms: dict[uuid.UUID, set[WebSocket]] = {}

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self.rooms.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        room = self.rooms.get(user_id)
        if room is not None:
            room.discard(websocket)
            if not room:
                self.rooms.pop(user_id, None)

    async def push(self, user_id: uuid.UUID, payload: dict) -> None:
        for ws in list(self.rooms.get(user_id, ())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(user_id, ws)


hub = NotificationHub()
