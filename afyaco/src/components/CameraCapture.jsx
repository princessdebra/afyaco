import { useEffect, useRef, useState } from 'react';
import { captureChallengeBurst } from '../api/identity';

// Hardware-free capture widget per the XIA brief §4.3, extended for
// challenge-response liveness: shows the server-issued instruction
// ("Turn your head left"), gives the member a moment to read it, then
// auto-captures a frame burst while they perform it. onCapture receives the
// full frames array (frame[0] is the frontal baseline shot).
export default function CameraCapture({ instruction, onCapture, disabled }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);
  const [phase, setPhase] = useState('idle'); // idle | countdown | capturing | done
  const [countdown, setCountdown] = useState(2);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError('This browser does not support camera access. Try a recent Chrome, Safari or Edge on your phone.');
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        setReady(true);
      } catch (err) {
        if (!cancelled) {
          setError(
            err.name === 'NotAllowedError'
              ? 'Camera permission was denied. Allow camera access and reload this page.'
              : err.name === 'NotFoundError'
              ? "No camera was found on this device. If you're on a laptop with a broken camera, try opening this on your phone instead."
              : `Could not start the camera (${err.name || 'unknown error'}).`
          );
        }
      }
    })();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  async function handleStart() {
    setPhase('countdown');
    for (let n = 2; n >= 1; n--) {
      setCountdown(n);
      await new Promise((r) => setTimeout(r, 700));
    }
    setPhase('capturing');
    const frames = await captureChallengeBurst(videoRef.current);
    setPhase('done');
    onCapture(frames);
  }

  if (error) {
    return <div className="notice info"><span>⚠</span><div>{error}</div></div>;
  }

  return (
    <div style={{ display: 'grid', gap: 10 }}>
      {instruction && phase !== 'idle' && (
        <div className="notice ok" style={{ fontWeight: 600 }}>
          <span>👤</span>
          <div>
            {phase === 'countdown' && `Get ready… ${countdown}`}
            {phase === 'capturing' && instruction}
            {phase === 'done' && 'Got it — processing…'}
          </div>
        </div>
      )}
      <video
        ref={videoRef}
        playsInline
        muted
        style={{ width: '100%', maxWidth: 420, borderRadius: 12, background: '#000', transform: 'scaleX(-1)' }}
      />
      {phase === 'idle' && (
        <>
          {instruction && (
            <div className="notice info">
              <span>ℹ</span>
              <div>When you click start, you'll have a moment to get ready, then be asked to: <b>{instruction}</b></div>
            </div>
          )}
          <button type="button" className="btn primary" disabled={!ready || disabled} onClick={handleStart}>
            Start
          </button>
        </>
      )}
    </div>
  );
}
