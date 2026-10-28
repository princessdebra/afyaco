import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Icon from '../components/Icon';
import { initials } from '../components/Brand';
import { api } from '../api/client';
import useWebRTC from '../hooks/useWebRTC';

function useElapsed(startedAt) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!startedAt) return;
    setSeconds(Math.floor((Date.now() - startedAt) / 1000));
    const id = setInterval(() => setSeconds(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => clearInterval(id);
  }, [startedAt]);
  const m = String(Math.floor(seconds / 60)).padStart(2, '0');
  const s = String(seconds % 60).padStart(2, '0');
  return `${m}:${s}`;
}

export default function VideoCall() {
  const { appointmentId } = useParams();
  const navigate = useNavigate();
  const localVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const streamRef = useRef(null);

  const [appointment, setAppointment] = useState(null);
  const [provider, setProvider] = useState(null);
  const [consultation, setConsultation] = useState(null);
  const [localStream, setLocalStream] = useState(null);
  const [error, setError] = useState('');
  const [camPermission, setCamPermission] = useState('pending'); // pending | granted | denied
  const [micOn, setMicOn] = useState(true);
  const [camOn, setCamOn] = useState(true);
  const [ending, setEnding] = useState(false);
  const [startedAt, setStartedAt] = useState(null);
  const elapsed = useElapsed(startedAt);

  const { remoteStream, callState, diag } = useWebRTC(consultation?.id, localStream);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [appt, providers] = await Promise.all([api.getAppointment(appointmentId), api.listProviders()]);
        if (cancelled) return;
        setAppointment(appt);
        setProvider(providers.find((p) => p.id === appt.provider_id) || null);
        let c;
        try {
          c = await api.startConsultation(appointmentId);
        } catch {
          // Already ended previously — still let the two sides reconnect
          // rather than dead-ending on "already completed".
          c = await api.getConsultationByAppointment(appointmentId);
        }
        if (cancelled) return;
        setConsultation(c);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not start this consultation.');
      }
    })();
    return () => { cancelled = true; };
  }, [appointmentId]);

  useEffect(() => {
    if (callState === 'connected' && !startedAt) setStartedAt(Date.now());
    if (callState === 'waiting') setStartedAt(null);
  }, [callState, startedAt]);

  async function requestCamera() {
    setCamPermission('pending');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 480 }, height: { ideal: 360 }, frameRate: { ideal: 15, max: 20 } }, audio: true });
      streamRef.current = stream;
      setLocalStream(stream);
      setCamPermission('granted');
    } catch {
      setCamPermission('denied');
    }
  }

  useEffect(() => {
    requestCamera();
    return () => streamRef.current?.getTracks().forEach((t) => t.stop());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // The <video> element for the self-view only exists in the DOM once
  // camPermission flips to 'granted' — assigning srcObject in requestCamera()
  // itself was a no-op (the ref was still null at that point, one render
  // too early). This effect re-runs once the element is actually mounted.
  useEffect(() => {
    if (camPermission === 'granted' && localVideoRef.current) localVideoRef.current.srcObject = localStream;
  }, [camPermission, localStream]);

  const [remoteBlocked, setRemoteBlocked] = useState(false);
  useEffect(() => {
    const el = remoteVideoRef.current;
    if (!el) return;
    el.srcObject = remoteStream;
    if (remoteStream) {
      // The remote video isn't muted (we want the clinician's audio), and
      // browsers require a real user gesture before an unmuted video is
      // allowed to autoplay. If that's blocked, this was the actual cause of
      // "connected but black screen" — show a tap-to-start overlay rather
      // than silently failing.
      el.play().then(() => setRemoteBlocked(false)).catch(() => setRemoteBlocked(true));
    }
  }, [remoteStream]);

  function toggleMic() {
    if (camPermission !== 'granted') return;
    streamRef.current?.getAudioTracks().forEach((t) => { t.enabled = !micOn; });
    setMicOn((v) => !v);
  }
  function toggleCam() {
    if (camPermission !== 'granted') return;
    streamRef.current?.getVideoTracks().forEach((t) => { t.enabled = !camOn; });
    setCamOn((v) => !v);
  }

  async function handleLeave() {
    setEnding(true);
    try {
      if (consultation) await api.endConsultation(consultation.id);
    } catch {
      // consultation end failing shouldn't trap the member in the call UI
    } finally {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      navigate('/portal/consultations');
    }
  }

  const apptTime = appointment ? new Date(appointment.scheduled_at) : null;
  const connected = callState === 'connected';

  return (
    <div style={{ position: 'fixed', inset: 0, background: '#0b1f1c', zIndex: 1000, display: 'grid', gridTemplateRows: 'auto 1fr auto', color: '#fff' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', padding: '10px 14px', background: 'rgba(255,255,255,.04)', borderBottom: '1px solid rgba(255,255,255,.08)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          <button className="btn sm" style={{ borderRadius: '50%', width: 32, height: 32, padding: 0, flexShrink: 0, background: 'transparent', color: '#fff', borderColor: 'rgba(255,255,255,.3)' }} onClick={() => navigate('/portal')} aria-label="Back to Home" title="Back to Home">
            <Icon name="home" />
          </button>
          <span className="avatar" style={{ background: 'rgba(255,255,255,.1)', color: '#fff', flexShrink: 0 }}>{provider ? initials(provider.name) : <Icon name="video" />}</span>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <b style={{ fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{provider?.name || 'Consultation'}</b>
              {provider?.specialties?.[0] && <span className="pill violet" style={{ fontSize: 10 }}>{provider.specialties[0]}</span>}
            </div>
            <div style={{ fontSize: 11.5, opacity: .75, display: 'flex', alignItems: 'center', gap: 6 }}>
              {connected ? (
                <><i style={{ width: 7, height: 7, borderRadius: '50%', background: '#2ecc71', display: 'inline-block' }} /> Live · {elapsed}</>
              ) : callState === 'failed' ? (
                <><i style={{ width: 7, height: 7, borderRadius: '50%', background: '#e8365d', display: 'inline-block' }} /> Connection failed</>
              ) : (
                <><span className="call-spinner" /> Connecting…</>
              )}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
          <span title="End-to-end session details are logged for your safety record" className="call-secure-label" style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, opacity: .7 }}>
            <Icon name="shield" style={{ width: 14, height: 14 }} /> Secure session
          </span>
          <button className="btn sm" style={{ background: 'transparent', color: '#fff', borderColor: 'rgba(255,255,255,.3)', whiteSpace: 'nowrap' }} onClick={() => navigate('/portal/consultations')}><Icon name="x" /> Minimize</button>
        </div>
      </div>
      {diag && (
        <div style={{ position: 'absolute', top: 54, left: 8, zIndex: 5, fontSize: 9.5, fontFamily: 'monospace', background: 'rgba(0,0,0,.55)', color: '#9effc0', padding: '4px 7px', borderRadius: 6, lineHeight: 1.5 }}>
          path:{diag.path} sent:{diag.sendingFrames} decoded:{diag.recvFrames} bytes:{diag.recvBytes} lost:{diag.packetsLost}
          {remoteStream?.getVideoTracks()[0] && (() => { const t = remoteStream.getVideoTracks()[0]; return <> trackMuted:{String(t.muted)} trackReady:{t.readyState}</>; })()}
        </div>
      )}

      <div style={{ position: 'relative', display: 'grid', placeItems: 'center', overflow: 'hidden', padding: 20 }}>
        {error && <div className="notice" style={{ maxWidth: 420 }}><Icon name="alert" /><div>{error}</div></div>}

        {!error && callState === 'failed' && (
          <div style={{ textAlign: 'center', maxWidth: 380 }}>
            <span className="tile-icon orange" style={{ margin: '0 auto 14px' }}><Icon name="alert" /></span>
            <b style={{ fontSize: 18, display: 'block' }}>Couldn't establish a connection</b>
            <p style={{ opacity: .7, fontSize: 13, margin: '8px 0 0' }}>This usually means one of the networks involved is blocking direct peer connections (common on strict corporate/mobile networks). Try a different network, or ask the other person to switch to wifi.</p>
          </div>
        )}

        {!error && !connected && callState !== 'failed' && (
          <div style={{ textAlign: 'center', maxWidth: 380 }}>
            <div style={{ position: 'relative', width: 96, height: 96, margin: '0 auto 18px' }}>
              <div className="call-pulse-ring" />
              <div className="avatar" style={{ width: 96, height: 96, fontSize: 32, position: 'relative', background: 'var(--teal-pale)', color: 'var(--teal-deep)' }}>
                <Icon name="stetho" style={{ width: 36, height: 36 }} />
              </div>
            </div>
            <b style={{ fontSize: 18, display: 'block' }}>Your consultation is starting soon</b>
            <p style={{ opacity: .7, fontSize: 13, margin: '8px 0 4px' }}>{provider?.name || 'Your clinician'} will join you shortly.</p>
            {apptTime && (
              <p style={{ opacity: .55, fontSize: 11.5, margin: '0 0 16px' }}>
                {apptTime.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} · {apptTime.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })} · Video consultation
              </p>
            )}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, fontSize: 12.5, color: 'var(--teal-primary, #3dd6b0)', margin: '0 0 16px' }}>
              <span className="call-spinner" /> {callState === 'connecting' ? 'Connecting…' : consultation ? 'Connecting you with your clinician…' : 'Setting up a secure session…'}
            </div>
            <div style={{ background: 'rgba(255,255,255,.06)', borderRadius: 12, padding: '10px 14px', textAlign: 'left' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5 }}><Icon name="video" style={{ width: 15, height: 15 }} /> Camera</span>
                <small style={{ color: camPermission === 'granted' ? '#2ecc71' : camPermission === 'denied' ? '#f0a742' : 'rgba(255,255,255,.5)' }}>
                  {camPermission === 'granted' ? 'Ready' : camPermission === 'denied' ? 'Permission needed' : 'Checking…'}
                </small>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5 }}><Icon name="mic" style={{ width: 15, height: 15 }} /> Microphone</span>
                <small style={{ color: camPermission === 'granted' ? '#2ecc71' : camPermission === 'denied' ? '#f0a742' : 'rgba(255,255,255,.5)' }}>
                  {camPermission === 'granted' ? 'Ready' : camPermission === 'denied' ? 'Check device' : 'Checking…'}
                </small>
              </div>
            </div>
          </div>
        )}

        {!error && connected && (
          <div style={{ position: 'relative', width: '100%', height: '100%' }}>
            {/* border-radius on a <video> itself renders blank/black in Safari —
                it has to live on this wrapper instead, with the video left square. */}
            <div style={{ width: '100%', height: '100%', borderRadius: 12, overflow: 'hidden', background: '#000' }}>
              <video key={remoteStream?.id || 'novideo'} ref={remoteVideoRef} autoPlay playsInline style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
            </div>
            {!remoteBlocked && !remoteStream?.getVideoTracks().length && (
              <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', textAlign: 'center', pointerEvents: 'none' }}>
                <div><span className="call-spinner" /> <span style={{ fontSize: 12.5, opacity: .8 }}>Connected — waiting for video…</span></div>
              </div>
            )}
            {remoteBlocked && (
              <button
                className="btn primary"
                style={{ position: 'absolute', inset: 0, margin: 'auto', width: 220, height: 48 }}
                onClick={() => remoteVideoRef.current?.play().then(() => setRemoteBlocked(false)).catch(() => {})}
              >
                <Icon name="video" /> Tap to start video
              </button>
            )}
            {!remoteBlocked && remoteStream?.getVideoTracks().length > 0 && (
              <button
                className="btn sm"
                style={{ position: 'absolute', left: '50%', bottom: 10, transform: 'translateX(-50%)', background: 'rgba(0,0,0,.55)', color: '#fff', borderColor: 'rgba(255,255,255,.3)' }}
                onClick={() => {
                  const el = remoteVideoRef.current;
                  if (!el) return;
                  el.srcObject = null;
                  el.load();
                  el.srcObject = remoteStream;
                  el.play().catch(() => {});
                }}
              >
                Video looks black? Tap to refresh
              </button>
            )}
          </div>
        )}

        <div style={{ position: 'absolute', right: 12, bottom: 12, width: 'min(220px, 36vw)', height: 'min(150px, 25vw)', minWidth: 110, minHeight: 75, borderRadius: 12, overflow: 'hidden', background: '#17302c', border: '2px solid rgba(255,255,255,.15)' }}>
          {camPermission === 'denied' ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 8, padding: 12, textAlign: 'center' }}>
              <Icon name="videoOff" style={{ width: 22, height: 22, opacity: .7 }} />
              <small style={{ fontSize: 10.5, opacity: .75, lineHeight: 1.3 }}>Camera unavailable — check your browser's site permissions</small>
              <button className="btn sm" style={{ height: 24, fontSize: 10, padding: '0 10px', background: 'transparent', color: '#fff', borderColor: 'rgba(255,255,255,.3)' }} onClick={requestCamera}>Check permissions</button>
            </div>
          ) : camPermission === 'pending' ? (
            <div style={{ display: 'grid', placeItems: 'center', height: '100%' }}><span className="call-spinner" /></div>
          ) : (
            <>
              <video ref={localVideoRef} autoPlay playsInline muted style={{ width: '100%', height: '100%', objectFit: 'cover', display: camOn ? 'block' : 'none' }} />
              {!camOn && <div style={{ display: 'grid', placeItems: 'center', height: '100%' }}><Icon name="videoOff" /></div>}
              <span style={{ position: 'absolute', left: 8, bottom: 6, fontSize: 10, opacity: .8, background: 'rgba(0,0,0,.35)', padding: '2px 6px', borderRadius: 6 }}>You</span>
            </>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', gap: 20, padding: '14px 0 26px' }}>
        <div style={{ textAlign: 'center' }}>
          <button
            className="btn"
            style={{ borderRadius: '50%', width: 52, height: 52, padding: 0, background: camPermission !== 'granted' ? 'rgba(255,255,255,.04)' : micOn ? 'rgba(255,255,255,.1)' : '#e8365d', borderColor: camPermission !== 'granted' ? 'rgba(255,255,255,.15)' : micOn ? 'rgba(255,255,255,.3)' : '#e8365d', color: camPermission !== 'granted' ? 'rgba(255,255,255,.35)' : '#fff', cursor: camPermission !== 'granted' ? 'not-allowed' : 'pointer' }}
            onClick={toggleMic}
            disabled={camPermission !== 'granted'}
            aria-label={micOn ? 'Mute microphone' : 'Unmute microphone'}
            title={camPermission !== 'granted' ? 'Microphone unavailable' : micOn ? 'Mute microphone' : 'Unmute microphone'}
          >
            <Icon name={micOn ? 'mic' : 'micOff'} />
          </button>
          <small style={{ display: 'block', fontSize: 10.5, opacity: .7, marginTop: 6 }}>{camPermission !== 'granted' ? 'Unavailable' : micOn ? 'Mute' : 'Muted'}</small>
        </div>
        <div style={{ textAlign: 'center' }}>
          <button
            className="btn"
            style={{ borderRadius: '50%', width: 52, height: 52, padding: 0, background: camPermission !== 'granted' ? 'rgba(255,255,255,.04)' : camOn ? 'rgba(255,255,255,.1)' : '#e8365d', borderColor: camPermission !== 'granted' ? 'rgba(255,255,255,.15)' : camOn ? 'rgba(255,255,255,.3)' : '#e8365d', color: camPermission !== 'granted' ? 'rgba(255,255,255,.35)' : '#fff', cursor: camPermission !== 'granted' ? 'not-allowed' : 'pointer' }}
            onClick={toggleCam}
            disabled={camPermission !== 'granted'}
            aria-label={camOn ? 'Turn camera off' : 'Turn camera on'}
            title={camPermission !== 'granted' ? 'Camera unavailable' : camOn ? 'Turn camera off' : 'Turn camera on'}
          >
            <Icon name={camOn ? 'video' : 'videoOff'} />
          </button>
          <small style={{ display: 'block', fontSize: 10.5, opacity: .7, marginTop: 6 }}>{camPermission !== 'granted' ? 'Unavailable' : camOn ? 'Camera' : 'Camera off'}</small>
        </div>
        <div style={{ textAlign: 'center' }}>
          <button className="btn danger" style={{ borderRadius: '50%', width: 52, height: 52, padding: 0 }} onClick={handleLeave} disabled={ending} aria-label="End call" title="End call">
            <Icon name="phone" style={{ transform: 'rotate(135deg)' }} />
          </button>
          <small style={{ display: 'block', fontSize: 10.5, opacity: .85, marginTop: 6 }}>{ending ? 'Ending…' : 'End call'}</small>
        </div>
      </div>
    </div>
  );
}
