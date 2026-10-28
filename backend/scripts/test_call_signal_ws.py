"""Smoke test for the WebRTC signaling relay — proves two independent logins
joining the same consultation's signal channel get the join/peer-joined
handshake and can relay arbitrary offer/answer/ICE payloads to each other.
Doesn't exercise real WebRTC (that needs an actual browser) — this only
proves the relay plumbing is correct.
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
    consultation_id = "76bfe688-7d3c-4cf8-b20a-49118114145e"

    member_ws = await websockets.connect(f"{WS_BASE}/api/v1/call/{consultation_id}/signal?token={member_token}")
    joined1 = json.loads(await member_ws.recv())
    print("member joined:", joined1)
    assert joined1 == {"type": "joined", "peer_present": False}

    clinician_ws = await websockets.connect(f"{WS_BASE}/api/v1/call/{consultation_id}/signal?token={clinician_token}")
    joined2 = json.loads(await clinician_ws.recv())
    print("clinician joined:", joined2)
    assert joined2 == {"type": "joined", "peer_present": True}

    peer_joined = json.loads(await asyncio.wait_for(member_ws.recv(), timeout=5))
    print("member sees peer-joined:", peer_joined)
    assert peer_joined == {"type": "peer-joined"}

    await clinician_ws.send(json.dumps({"type": "offer", "sdp": "FAKE_SDP_OFFER"}))
    relayed_offer = json.loads(await asyncio.wait_for(member_ws.recv(), timeout=5))
    print("member received relayed offer:", relayed_offer)
    assert relayed_offer == {"type": "offer", "sdp": "FAKE_SDP_OFFER"}

    await member_ws.send(json.dumps({"type": "answer", "sdp": "FAKE_SDP_ANSWER"}))
    relayed_answer = json.loads(await asyncio.wait_for(clinician_ws.recv(), timeout=5))
    print("clinician received relayed answer:", relayed_answer)
    assert relayed_answer == {"type": "answer", "sdp": "FAKE_SDP_ANSWER"}

    await member_ws.close()
    peer_left = json.loads(await asyncio.wait_for(clinician_ws.recv(), timeout=5))
    print("clinician sees peer-left:", peer_left)
    assert peer_left == {"type": "peer-left"}

    await clinician_ws.close()
    print("\nALL CHECKS PASSED — signaling relay works correctly")


asyncio.run(main())
