import { useEffect, useState } from 'react';
import { initials } from '../../components/Brand';
import { api } from '../../api/client';

const STATUS_TONE = { approved: '', paid: '', in_review: 'orange', needs_action: 'red', rejected: 'red', submitted: 'blue', draft: 'gray' };

function fmtDate(iso) {
  return iso ? new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—';
}

export default function ProviderClaims() {
  const [claims, setClaims] = useState(null);
  const [members, setMembers] = useState({});
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await api.listMyPatientsClaims();
        if (cancelled) return;
        setClaims(list);
        const ids = [...new Set(list.map((c) => c.member_id))];
        const fetched = await Promise.all(ids.map((id) => api.getMemberById(id).catch(() => null)));
        if (cancelled) return;
        const next = {};
        ids.forEach((id, i) => { if (fetched[i]) next[id] = fetched[i]; });
        setMembers(next);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load claims.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <>
      <div className="page-title"><div><h1>Claims</h1><p>Claims for members you've seen, across all their visits — not just with you.</p></div></div>
      {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}
      <section className="card">
        {!claims && !error && <p className="slate" style={{ padding: 20 }}>Loading…</p>}
        {claims && claims.length === 0 && <p className="slate" style={{ padding: 20 }}>No claims for your patients yet.</p>}
        {claims && claims.length > 0 && (
          <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Patient</th><th>Service</th><th>Amount</th><th>Status</th><th>Submitted</th></tr></thead>
            <tbody>
              {claims.map((c) => {
                const member = members[c.member_id];
                const line = c.lines?.[0] || {};
                return (
                  <tr key={c.id}>
                    <td style={{ display: 'flex', alignItems: 'center', gap: 8 }}><span className="avatar" style={{ width: 28, height: 28, fontSize: 11 }}>{member ? initials(member.full_name) : '…'}</span>{member?.full_name || 'Loading…'}</td>
                    <td>{line.service || '—'}<br /><small className="muted">{c.external_claim_id || c.id.slice(0, 8)}</small></td>
                    <td>KES {(line.amount || 0).toLocaleString()}</td>
                    <td><span className={`pill ${STATUS_TONE[c.status] || ''}`}>{c.status.replace('_', ' ')}</span></td>
                    <td>{fmtDate(c.submitted_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
        )}
      </section>
    </>
  );
}
