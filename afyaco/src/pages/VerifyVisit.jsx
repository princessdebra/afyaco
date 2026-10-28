import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import CameraCapture from '../components/CameraCapture';
import { PageTitle } from '../components/Brand';
import { identityApi, getLocationSignal } from '../api/identity';

export default function VerifyVisit() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const facilityId = params.get('facility') || '';

  const [step, setStep] = useState(token && facilityId ? 'starting' : 'missing');
  const [challenge, setChallenge] = useState(null); // {liveness_challenge_id, instruction, encounter_id}
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const startedRef = useRef(false); // guards against React 18 StrictMode's double-invoked dev effects consuming the single-use QR token twice
  const locationPromiseRef = useRef(null); // kicked off as soon as we're ready, so the permission prompt/GPS fix overlaps with reading the instruction + capturing, instead of adding to the critical path after

  useEffect(() => {
    if (step !== 'starting') return;
    if (startedRef.current) return;
    startedRef.current = true;
    (async () => {
      try {
        const ch = await identityApi.startVerification(token, facilityId);
        setChallenge(ch);
        locationPromiseRef.current = getLocationSignal();
        setStep('ready');
      } catch (err) {
        setError(err.message || 'Could not start verification — this QR code may have expired or already been used.');
        setStep('error');
      }
    })();
  }, [step, token, facilityId]);

  async function handleCapture(frames) {
    setBusy(true);
    setError('');
    try {
      const location = await (locationPromiseRef.current || getLocationSignal());
      const res = await identityApi.completeVerification(challenge.liveness_challenge_id, frames, location);
      setResult(res);
      setStep('done');
    } catch (err) {
      setError(err.message || 'Verification failed.');
    } finally {
      setBusy(false);
    }
  }

  async function handleRetry() {
    setBusy(true);
    setError('');
    try {
      const ch = await identityApi.retryVerification(result.encounter_id);
      setChallenge(ch);
      locationPromiseRef.current = getLocationSignal();
      setResult(null);
      setStep('ready');
    } catch (err) {
      setError(err.message || 'Could not start a new attempt.');
    } finally {
      setBusy(false);
    }
  }

  if (step === 'missing') {
    return (
      <>
        <PageTitle title="Verify your visit" sub="This page is opened by scanning a hospital's QR code — it isn't meant to be visited directly." />
        <div className="notice info"><span>⚠</span><div>No verification challenge was found in this link. Ask the hospital front desk for a fresh QR code.</div></div>
      </>
    );
  }

  const canRetry = result && (result.overall_outcome === 'failed' || result.overall_outcome === 'manual_review_required') && result.encounter_status !== 'verified';

  return (
    <>
      <PageTitle title="Verify your visit" sub="Take a photo to confirm your identity for this hospital visit. This does not by itself confirm your insurance cover." />
      {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}

      {step === 'starting' && <p className="slate">Starting verification…</p>}

      {step === 'ready' && challenge && (
        <section className="card">
          <p className="slate" style={{ fontSize: 13, marginBottom: 12 }}>
            We'll also ask for your device location to help confirm you're at the facility — this is optional and only used for this visit.
          </p>
          <CameraCapture instruction={challenge.instruction} onCapture={handleCapture} disabled={busy} />
        </section>
      )}

      {step === 'done' && result && (
        <section className="card">
          {result.overall_outcome === 'passed' && (
            <div className="notice ok" style={{ fontSize: 15, padding: 16, marginBottom: 16 }}>
              <span style={{ fontSize: 22 }}>✅</span>
              <div>
                <b>{result.member_name} has been successfully verified at {result.facility_name}.</b><br />
                <small className="slate">
                  {result.location_outcome === 'accepted'
                    ? `Your device's location was confirmed within range of ${result.facility_name}.`
                    : "Your device location wasn't used to confirm this — identity was still verified by face and challenge-response."}
                </small>
              </div>
            </div>
          )}
          {result.overall_outcome === 'manual_review_required' && (
            <div className="notice info" style={{ fontSize: 15, padding: 16, marginBottom: 16 }}>
              <span style={{ fontSize: 22 }}>ℹ️</span>
              <div>
                <b>{result.member_name}'s identity looks correct at {result.facility_name}, but needs a quick human check.</b><br />
                <small className="slate">Hospital staff will confirm you in manually — this is routine, not a sign of a problem.</small>
              </div>
            </div>
          )}
          {result.overall_outcome === 'failed' && (
            <div className="notice info" style={{ fontSize: 15, padding: 16, marginBottom: 16, borderColor: 'var(--warn-orange, #c0392b)' }}>
              <span style={{ fontSize: 22 }}>⚠️</span>
              <div><b>We couldn't verify {result.member_name} at {result.facility_name} automatically.</b></div>
            </div>
          )}

          {/* Only actionable, member-relevant detail is shown here — the full
              technical breakdown (quality/liveness/match/eligibility) is
              provider-facing only, viewed by hospital staff on their side. */}
          {result.challenge_response_outcome !== 'passed' && (
            <div className="notice info" style={{ marginBottom: 12 }}>
              <span>{result.challenge_response_outcome === 'failed' ? '⚠' : 'ℹ'}</span>
              <div><b>{result.challenge_response_detail}</b></div>
            </div>
          )}
          {['out_of_range', 'implausible', 'stale'].includes(result.location_outcome) && (
            <div className="notice info" style={{ marginBottom: 12 }}>
              <span>ℹ</span>
              <div><b>We couldn't confirm your location is at {result.facility_name}.</b> Make sure location access is allowed for this site and you're within the facility.</div>
            </div>
          )}

          {result.overall_outcome === 'failed' && (
            <div className="notice info"><span>⚠</span><div>This is not treated as fraud — you can try again below, or ask hospital staff for the alternative verification process.</div></div>
          )}

          {canRetry && (
            <button className="btn primary" style={{ marginTop: 12 }} disabled={busy} onClick={handleRetry}>
              {busy ? 'Starting…' : 'Try again'}
            </button>
          )}
        </section>
      )}
    </>
  );
}
