"""One-off smoke test: proves the chat WebSocket actually delivers messages
in real time between two different logged-in users (member + clinician),
not just that REST endpoints respond. Not part of the pytest suite.
"""
import asyncio
import json

import httpx
import websockets

BASE = "http://127.0.0.1:9028"
WS_BASE = "ws://127.0.0.1:9028"


async def login(tenant, email, password):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE}/api/v1/auth/login", json={"tenant_slug": tenant, "email": email, "password": password})
        r.raise_for_status()
        return r.json()["access_token"]


async def main():
    member_token = await login("jubilee", "member@jubilee.test", "ChangeMe123!")
    clinician_token = await login("jubilee", "clinician@jubilee.test", "ChangeMe123!")

    # Reuses an existing consultation (already completed from earlier manual
    # testing) rather than appointments/start, which refuses to restart one —
    # fine here since this test only exercises the chat channel, not the
    # consultation lifecycle.
    consultation_id = "76bfe688-7d3c-4cf8-b20a-49118114145e"
    print("consultation:", consultation_id)

    member_ws = await websockets.connect(f"{WS_BASE}/api/v1/chat/{consultation_id}/ws?token={member_token}")
    clinician_ws = await websockets.connect(f"{WS_BASE}/api/v1/chat/{consultation_id}/ws?token={clinician_token}")
    print("both connected")

    # Broadcasts go to every connection in the room, sender included — the
    # client never optimistically renders its own send, it just waits for
    # this echo, so there's one source of truth for message order/state.
    await member_ws.send(json.dumps({"type": "message", "body": "Hello doctor, from the MEMBER device"}))
    member_echo = json.loads(await asyncio.wait_for(member_ws.recv(), timeout=5))
    print("member's own echo:", member_echo)
    received_by_clinician = json.loads(await asyncio.wait_for(clinician_ws.recv(), timeout=5))
    print("clinician received:", received_by_clinician)
    assert received_by_clinician["body"] == "Hello doctor, from the MEMBER device"
    assert received_by_clinician["sender_role"] == "member"

    await clinician_ws.send(json.dumps({"type": "message", "body": "Hi! This is the CLINICIAN device replying"}))
    clinician_echo = json.loads(await asyncio.wait_for(clinician_ws.recv(), timeout=5))
    print("clinician's own echo:", clinician_echo)
    received_by_member = json.loads(await asyncio.wait_for(member_ws.recv(), timeout=5))
    print("member received:", received_by_member)
    assert received_by_member["body"] == "Hi! This is the CLINICIAN device replying"
    assert received_by_member["sender_role"] == "clinician"

    await clinician_ws.send(json.dumps({"type": "typing"}))
    clinician_typing_echo = json.loads(await asyncio.wait_for(clinician_ws.recv(), timeout=5))
    assert clinician_typing_echo["type"] == "typing"
    typing_event = json.loads(await asyncio.wait_for(member_ws.recv(), timeout=5))
    print("member saw typing event:", typing_event)
    assert typing_event["type"] == "typing"

    await member_ws.send(json.dumps({"type": "read"}))
    member_read_echo = json.loads(await asyncio.wait_for(member_ws.recv(), timeout=5))
    assert member_read_echo["type"] == "read"
    read_event = json.loads(await asyncio.wait_for(clinician_ws.recv(), timeout=5))
    print("clinician saw read receipt:", read_event)
    assert read_event["type"] == "read"

    await member_ws.close()
    await clinician_ws.close()
    print("\nALL CHECKS PASSED — real two-way chat confirmed between two independent logins")


asyncio.run(main())
