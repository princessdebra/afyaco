import { useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';
import { PageTitle } from '../../components/Brand';
import { api } from '../../api/client';
import { identityApi } from '../../api/identity';

const OUTCOME_TONE = {
  acceptable: '', passed: '', match: '', accepted: '', confirmed: '', not_eligible: 'red',
  rejected: 'red', failed: 'red', no_match: 'red', not_enrolled: 'red', out_of_range: 'orange',
  implausible: 'orange', stale: 'orange', unavailable: 'gray', pending: 'orange',
  manual_review_required: 'orange', provider_unavailable: 'orange',
};

function Badge({ label, value }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="card" style={{ padding: 10 }}>
      <small className="slate">{label}</small><br />
      <span className={`pill ${OUTCOME_TONE[value] || 'gray'}`}>{String(value).replace(/_/g, ' ')}</span>
    </div>
  );
}

export default function HospitalEncounter() {
  const [facilities, setFacilities] = useState([]);
  const [facilityId, setFacilityId] = useState('');
  const [memberRef, setMemberRef] = useState('MNT-0942-SC8591');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [encounter, setEncounter] = useState(null);
  const [attempt, setAttempt] = useState(null);
  const [challenge, setChallenge] = useState(null);
  const [qrDataUrl, setQrDataUrl] = useState('');
  const [secondsLeft, setSecondsLeft] = useState(0);
  const pollRef = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const list = await api.listProviders({ type: 'facility' });
        setFacilities(list);
        if (list[0]) setFacilityId(list[0].id);
      } catch (err) {
        setError(err.message || 'Could not load facilities.');
      }
    })();
  }, []);

  useEffect(() => {
    if (!challenge) return undefined;
    const tick = () => {
      const left = Math.max(0, Math.round((new Date(challenge.expires_at) - Date.now()) / 1000));
      setSecondsLeft(left);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [challenge]);

  useEffect(() => {
    if (!encounter) return undefined;
    pollRef.current = setInterval(async () => {
      try {
        const updated = await identityApi.getEncounter(encounter.id);
        setEncounter(updated);
        if (updated.identity_status !== 'not_started' && updated.identity_status !== 'in_progress') {
          identityApi.getEncounterAttempt(encounter.id).then(setAttempt).catch(() => {});
        }
        if (updated.status !== 'challenge_issued' && updated.status !== 'verifying' && updated.status !== 'created') {
          clearInterval(pollRef.current);
        }
      } catch {
        /* transient — next tick retries */
      }
    }, 3000);
    return () => clearInterval(pollRef.current);
  }, [encounter?.id]);

  async function startEncounter() {
    setBusy(true);
    setError('');
    setEncounter(null);
    setAttempt(null);
    setChallenge(null);
    setQrDataUrl('');
    try {
      const member = await api.getMember(memberRef);
      const enc = await identityApi.createEncounter(member.id, facilityId);
      setEncounter(enc);
      const ch = await identityApi.issueChallenge(enc.id);
      setChallenge(ch);
      const url = `${window.location.origin}/portal/verify-visit?token=${encodeURIComponent(ch.token)}&facility=${encodeURIComponent(facilityId)}`;
      setQrDataUrl(await QRCode.toDataURL(url, { width: 220, margin: 1 }));
    } catch (err) {
      setError(err.message || 'Could not start the encounter.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageTitle title="Hospital check-in" sub="Start a visit, generate a one-time QR code, and the member scans it on their own phone to verify their identity." />
      {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}

      <section className="card">
        <div className="grid g2" style={{ marginBottom: 12 }}>
          <label className="field">Member reference
            <input className="sel" value={memberRef} onChange={(e) => setMemberRef(e.target.value)} placeholder="e.g. MNT-0942-SC8591" />
          </label>
          <label className="field">Facility
            <select className="sel" value={facilityId} onChange={(e) => setFacilityId(e.target.value)}>
              {facilities.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </label>
        </div>
        <button className="btn primary" disabled={busy || !facilityId} onClick={startEncounter}>
          {busy ? 'Starting…' : 'Start encounter + generate QR'}
        </button>
      </section>

      {encounter && (
        <section className="card" style={{ marginTop: 16, display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <div>
            {qrDataUrl && <img src={qrDataUrl} alt="Scan to verify" width={220} height={220} />}
            {challenge && <p className="slate" style={{ fontSize: 12, marginTop: 8 }}>Expires in {secondsLeft}s — single use.</p>}
          </div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <h3 style={{ marginBottom: 8 }}>Encounter status</h3>
            <p className="slate" style={{ fontSize: 13 }}>
              Encounter: <span className="pill">{encounter.status}</span><br />
              Identity: <span className="pill">{encounter.identity_status}</span><br />
              Eligibility: <span className="pill">{encounter.eligibility_status}</span>
            </p>
          </div>
        </section>
      )}

      {attempt && (
        <section className="card" style={{ marginTop: 16 }}>
          <div className="card-head">
            <h3>Verification detail — {attempt.member_name}</h3>
            <span className={`pill ${OUTCOME_TONE[attempt.overall_outcome] || 'gray'}`}>{attempt.overall_outcome.replace(/_/g, ' ')}</span>
          </div>
          <div className="grid g3" style={{ marginTop: 12 }}>
            <Badge label="Capture quality" value={attempt.quality_outcome} />
            <Badge label="Passive liveness" value={attempt.liveness_outcome} />
            <Badge label="Head-movement check" value={attempt.challenge_response_outcome} />
            <Badge label="Face match" value={attempt.match_outcome} />
            <Badge label="Match score" value={attempt.match_score != null ? attempt.match_score.toFixed(2) : null} />
            <Badge label="Location" value={attempt.location_outcome} />
            <Badge label="Distance from facility" value={attempt.location_distance_m != null ? `${Math.round(attempt.location_distance_m)}m` : null} />
          </div>
          <p className="slate" style={{ fontSize: 11, marginTop: 10 }}>
            Attempt recorded {new Date(attempt.created_at).toLocaleString()} · staff-only detail, not shown to the member
          </p>
        </section>
      )}
    </>
  );
}
