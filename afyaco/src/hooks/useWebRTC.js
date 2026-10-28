import { useEffect, useRef, useState } from 'react';
import { callSignalWsUrl } from '../api/client';

// STUN alone only gets two peers connected if at least one of them has a
// NAT that allows a direct path in — mobile hotspots and many corporate/
// carrier networks block that (device isolation, symmetric NAT), which is
// exactly when a TURN relay is needed: both sides send media to it instead
// of to each other.
const ICE_SERVERS = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' },
  // Self-hosted coturn on the devserver — not reachable yet (port 3478 and
  // the relay range still need forwarding at the network level, outside
  // what's configurable from this app). Left in so it starts working the
  // moment that's done, with no further code change.
  { urls: 'turn:41.90.122.129:3478?transport=udp', username: 'afyaco_turn', credential: '9c293b937a6dcccc8c6d9a307dd5356b' },
  { urls: 'turn:41.90.122.129:3478?transport=tcp', username: 'afyaco_turn', credential: '9c293b937a6dcccc8c6d9a307dd5356b' },
  // TEMPORARY, for testing only — Open Relay Project's free public TURN
  // service, reachable right now over 80/443. Real call media would transit
  // a third-party server we have no agreement with; pull this once our own
  // coturn's ports are forwarded (see the entries above).
  { urls: 'turn:openrelay.metered.ca:80', username: 'openrelayproject', credential: 'openrelayproject' },
  { urls: 'turn:openrelay.metered.ca:443', username: 'openrelayproject', credential: 'openrelayproject' },
  { urls: 'turn:openrelay.metered.ca:443?transport=tcp', username: 'openrelayproject', credential: 'openrelayproject' },
];

// Real peer-to-peer WebRTC — the signaling (who's calling whom, SDP offer/
// answer, ICE candidates) goes through our own WebSocket relay
// (app/api/v1/call.py); once connected, audio/video flows directly between
// the two browsers, never through our server.
export default function useWebRTC(consultationId, localStream) {
  const [remoteStream, setRemoteStream] = useState(null);
  const [callState, setCallState] = useState('idle'); // idle | waiting | connecting | connected | failed
  const [diag, setDiag] = useState(null);
  const pcRef = useRef(null);

  useEffect(() => {
    if (!consultationId || !localStream) return;
    let closed = false;
    let makingOffer = false;

    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    pcRef.current = pc;
    // getUserMedia's track order isn't guaranteed to match across devices
    // (e.g. Android Chrome vs iOS Safari can hand back [audio, video] on one
    // phone and [video, audio] on the other) — forcing the same explicit
    // order on both ends avoids any m-line ordering disagreement. Plain
    // addTrack (not addTransceiver) deliberately: addTransceiver creates the
    // transceiver before any offer/answer has happened, and on Safari that
    // was silently leaving the sender unable to actually transmit frames —
    // addTrack lets the browser wire up transceivers during normal O/A,
    // the well-tested path.
    const videoTrack = localStream.getVideoTracks()[0];
    const audioTrack = localStream.getAudioTracks()[0];
    if (videoTrack) pc.addTrack(videoTrack, localStream);
    if (audioTrack) pc.addTrack(audioTrack, localStream);

    const ws = new WebSocket(callSignalWsUrl(consultationId));
    setCallState('waiting');

    // Real phones, not devtools — this is the only way to see what's
    // actually happening on a live call without plugging a phone into a
    // computer. Surfaced on-screen by the call pages rather than just logged.
    const statsInterval = setInterval(async () => {
      if (closed) return;
      try {
        const stats = await pc.getStats();
        let pair = null, videoIn = null, videoOut = null;
        stats.forEach((r) => {
          if (r.type === 'candidate-pair' && (r.state === 'succeeded' || r.selected)) pair = r;
          if (r.type === 'inbound-rtp' && r.kind === 'video') videoIn = r;
          if (r.type === 'outbound-rtp' && r.kind === 'video') videoOut = r;
        });
        let localType = '?', remoteType = '?';
        if (pair) {
          stats.forEach((r) => {
            if (r.id === pair.localCandidateId) localType = r.candidateType;
            if (r.id === pair.remoteCandidateId) remoteType = r.candidateType;
          });
        }
        setDiag({
          path: pair ? `${localType}->${remoteType}` : 'none',
          sendingFrames: videoOut?.framesSent ?? 0,
          recvFrames: videoIn?.framesDecoded ?? 0,
          recvBytes: videoIn?.bytesReceived ?? 0,
          packetsLost: videoIn?.packetsLost ?? 0,
          jitterBufferDelay: videoIn?.jitterBufferDelay != null ? Math.round(videoIn.jitterBufferDelay * 10) / 10 : null,
        });
      } catch {
        // getStats isn't critical — just skip this tick.
      }
    }, 2000);

    // ICE candidates can arrive over the signaling channel before
    // setRemoteDescription has run (race is normal, not a bug) — addIceCandidate
    // throws if called too early, so queue them and flush once it's set.
    // Silently swallowing that error (as before) was dropping real candidates,
    // which matters a lot without a TURN server: every path we can suggest
    // for the browsers to try increases the odds the call actually connects.
    let remoteDescriptionSet = false;
    let pendingCandidates = [];
    function flushPendingCandidates() {
      const queued = pendingCandidates;
      pendingCandidates = [];
      queued.forEach((c) => pc.addIceCandidate(c).catch(() => {}));
    }

    async function makeOffer() {
      if (makingOffer) return;
      makingOffer = true;
      try {
        setCallState('connecting');
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        ws.send(JSON.stringify({ type: 'offer', sdp: pc.localDescription }));
      } finally {
        makingOffer = false;
      }
    }

    pc.ontrack = (e) => {
      // Fires as soon as the remote SDP names this track — well before media
      // is actually flowing. It only tells us WHAT will arrive, not that the
      // connection is live; "connected" is driven by connectionstatechange
      // below. Flipping the UI here was the bug: both sides would show a
      // <video> element with nothing in it (a black box) the moment
      // signaling finished, even if ICE/DTLS never actually connected.
      if (closed) return;
      setRemoteStream(e.streams[0]);
    };
    pc.onconnectionstatechange = () => {
      if (closed) return;
      if (pc.connectionState === 'connected') setCallState('connected');
      else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') setCallState('failed');
    };
    pc.onicecandidate = (e) => {
      if (e.candidate && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ice-candidate', candidate: e.candidate }));
      }
    };

    ws.onmessage = async (evt) => {
      if (closed) return;
      const data = JSON.parse(evt.data);
      if (data.type === 'joined') {
        // Only the one who joined second initiates the offer — deterministic,
        // avoids both sides racing to offer at once (SDP glare).
        if (data.peer_present) await makeOffer();
      } else if (data.type === 'offer') {
        setCallState('connecting');
        await pc.setRemoteDescription(data.sdp);
        remoteDescriptionSet = true;
        flushPendingCandidates();
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        ws.send(JSON.stringify({ type: 'answer', sdp: pc.localDescription }));
      } else if (data.type === 'answer') {
        await pc.setRemoteDescription(data.sdp);
        remoteDescriptionSet = true;
        flushPendingCandidates();
      } else if (data.type === 'ice-candidate') {
        if (remoteDescriptionSet) pc.addIceCandidate(data.candidate).catch(() => {});
        else pendingCandidates.push(data.candidate);
      } else if (data.type === 'peer-left') {
        setRemoteStream(null);
        setCallState('waiting');
      }
    };

    return () => {
      closed = true;
      clearInterval(statsInterval);
      ws.close();
      pc.close();
      pcRef.current = null;
    };
  }, [consultationId, localStream]);

  return { remoteStream, callState, diag };
}
