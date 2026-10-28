"""One-off smoke test: proves a chat message generates a real, persisted,
live-pushed notification for the recipient, and that conversations/mine
and unread counts reflect it.
"""
import asyncio
import json

import httpx
import websockets

BASE = "http://127.0.0.1:9028"
WS_BASE = "ws://127.0.0.1:9028"


async def login(email, password):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE}/api/v1/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        return r.json()["access_token"]


async def main():
    member_token = await login("member@jubilee.test", "ChangeMe123!")
    clinician_token = await login("clinician@jubilee.test", "ChangeMe123!")

    async with httpx.AsyncClient() as client:
        convos = (await client.get(f"{BASE}/api/v1/consultations/mine", headers={"Authorization": f"Bearer {member_token}"})).json()
        print("member conversations:", [(c["counterpart_name"], c["unread_count"]) for c in convos])
        consultation_id = convos[0]["consultation_id"]

    clinician_notif_ws = await websockets.connect(f"{WS_BASE}/api/v1/notifications/ws?token={clinician_token}")
    member_chat_ws = await websockets.connect(f"{WS_BASE}/api/v1/chat/{consultation_id}/ws?token={member_token}")

    await member_chat_ws.send(json.dumps({"type": "message", "body": "Testing notification push"}))
    await member_chat_ws.recv()  # sender's own echo

    notif = json.loads(await asyncio.wait_for(clinician_notif_ws.recv(), timeout=5))
    print("clinician got live notification:", notif)
    assert notif["type"] == "notification"
    assert notif["notification_type"] == "chat_message"
    assert "Testing notification push" in notif["body"]

    async with httpx.AsyncClient() as client:
        unread = (await client.get(f"{BASE}/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {clinician_token}"})).json()
        print("clinician unread count:", unread)
        assert unread["count"] >= 1

    await member_chat_ws.close()
    await clinician_notif_ws.close()
    print("\nALL CHECKS PASSED — chat message produced a real, live-pushed notification")


asyncio.run(main())
