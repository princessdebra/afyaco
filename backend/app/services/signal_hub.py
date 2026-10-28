import uuid

from fastapi import WebSocket


class SignalHub:
    """WebRTC signaling relay — a dumb pass-through for SDP offers/answers and
    ICE candidates between the two participants of a consultation's video
    call. Unlike ChatHub, this never echoes back to the sender: there are
    only ever two peers in a 1:1 call, so "the room" and "the other peer"
    are the same thing. Same single-process limitation as ChatHub/NotificationHub.
    """

    def __init__(self) -> None:
        self.rooms: dict[uuid.UUID, set[WebSocket]] = {}

    async def connect(self, consultation_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        room = self.rooms.setdefault(consultation_id, set())
        # Tell the new arrival whether a peer is already waiting, and tell
        # that existing peer someone just joined — lets the frontend decide
        # who initiates the SDP offer without a race.
        peer_already_present = len(room) > 0
        room.add(websocket)
        await websocket.send_json({"type": "joined", "peer_present": peer_already_present})
        if peer_already_present:
            await self.relay(consultation_id, websocket, {"type": "peer-joined"})

    def disconnect(self, consultation_id: uuid.UUID, websocket: WebSocket) -> None:
        room = self.rooms.get(consultation_id)
        if room is not None:
            room.discard(websocket)
            if not room:
                self.rooms.pop(consultation_id, None)

    async def relay(self, consultation_id: uuid.UUID, sender: WebSocket, payload: dict) -> None:
        for ws in list(self.rooms.get(consultation_id, ())):
            if ws is sender:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(consultation_id, ws)


hub = SignalHub()
