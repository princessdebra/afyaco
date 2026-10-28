import { useEffect, useRef, useState } from 'react';
import CameraCapture from '../components/CameraCapture';
import { PageTitle } from '../components/Brand';
import { identityApi } from '../api/identity';
import { getCurrentMemberId, session } from '../api/client';

export default function Enroll() {
  const [memberId, setMemberId] = useState(null);
  const [enrollment, setEnrollment] = useState(undefined); // undefined = loading, null = none
  const [consented, setConsented] = useState(false);
  const [challenge, setChallenge] = useState(null); // {liveness_challenge_id, instruction}
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const bannerRef = useRef(null);

  useEffect(() => {
    if ((success || error) && bannerRef.current) {
      bannerRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [success, error]);

  useEffect(() => {
    (async () => {
      try {
        const id = await getCurrentMemberId();
        setMemberId(id);
        const existing = await identityApi.getEnrollment(id);
        setEnrollment(existing);
      } catch (err) {
        setError(err.message || 'Could not load enrollment status.');
        setEnrollment(null);
      }
    })();
  }, []);

  async function handleStartCapture() {
    setError('');
    setSuccess('');
    try {
      const ch = await identityApi.beginEnrollmentChallenge(memberId);
      setChallenge(ch);
    } catch (err) {
      setError(err.message || 'Could not start enrollment.');
    }
  }

  async function handleCapture(frames) {
    setBusy(true);
    setError('');
    setSuccess('');
    try {
      const result = await identityApi.createEnrollment(memberId, challenge.liveness_challenge_id, frames, `consent-web-${Date.now()}`);
      setEnrollment(result);
      setSuccess('Saved! Your facial reference has been enrolled successfully.');
      setChallenge(null);
    } catch (err) {
      setError(err.message || 'Enrollment failed. Nothing was saved — please try again.');
      setChallenge(null); // the challenge is single-use either way — let them request a fresh one
    } finally {
      setBusy(false);
    }
  }

  async function handleRevoke() {
    setBusy(true);
    setError('');
    try {
      await identityApi.revokeEnrollment(enrollment.id);
      setEnrollment(null);
      setSuccess('Your enrollment has been revoked. You can re-enroll at any time.');
    } catch (err) {
      setError(err.message || 'Could not revoke enrollment.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageTitle title="Identity Verification (XIA)" sub="Enroll your face once so you can verify your identity at a hospital using just your phone — no scanner required." />
      <div ref={bannerRef} />
      {error && (
        <div className="notice info" style={{ borderColor: 'var(--warn-orange, #c0392b)' }}>
          <span>⚠</span><div><b>{error}</b></div>
        </div>
      )}
      {success && (
        <div className="notice ok" style={{ fontSize: 15, padding: 16 }}>
          <span style={{ fontSize: 20 }}>✅</span><div><b>{success}</b></div>
        </div>
      )}

      <section className="card" style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 10 }}>What this is and how it works</h3>
        <ul className="slate" style={{ fontSize: 13, lineHeight: 1.7, paddingLeft: 18 }}>
          <li>You'll be asked to make a small head movement (e.g. turn left) when you enroll and again at the hospital — this proves it's really you, live, not a photo.</li>
          <li>A hospital will show a one-time QR code when you check in. Scanning it opens a page asking for a fresh photo of your face.</li>
          <li>Xenova compares that photo to the reference you create below — it never compares your face against anyone else's.</li>
          <li>Your enrolled reference is stored as a protected template, not as a photo others can view.</li>
          <li>A successful match confirms your identity only — it does not by itself confirm your insurance cover; that is checked separately with {session.tenantName || 'your insurer'}.</li>
          <li>You can revoke this enrollment at any time below, and re-enroll later.</li>
          <li>If facial verification doesn't work for you, hospital staff have an alternative, audited verification process.</li>
        </ul>
      </section>

      {enrollment === undefined && <p className="slate" style={{ marginTop: 16 }}>Loading…</p>}

      {enrollment === null && (
        <section className="card" style={{ marginTop: 16 }}>
          <h3 style={{ marginBottom: 10 }}>Enroll your face</h3>
          {!challenge ? (
            <>
              <label className="check" style={{ marginBottom: 12 }}>
                <input type="checkbox" checked={consented} onChange={(e) => setConsented(e.target.checked)} />
                {' '}I understand how my facial data will be used and stored, and I consent to enrollment.
              </label>
              <button className="btn primary" disabled={!consented} onClick={handleStartCapture}>
                {error ? 'Try again' : 'Start camera'}
              </button>
            </>
          ) : (
            <CameraCapture instruction={challenge.instruction} onCapture={handleCapture} disabled={busy} />
          )}
        </section>
      )}

      {enrollment && (
        <section className="card" style={{ marginTop: 16 }}>
          <h3 style={{ marginBottom: 10 }}>Enrollment status</h3>
          <p className="slate" style={{ fontSize: 13 }}>
            Status: <span className="pill">{enrollment.status}</span><br />
            Enrolled: {new Date(enrollment.created_at).toLocaleString()}
          </p>
          <button className="btn" style={{ marginTop: 10 }} disabled={busy} onClick={handleRevoke}>
            Revoke enrollment
          </button>
        </section>
      )}
    </>
  );
}
