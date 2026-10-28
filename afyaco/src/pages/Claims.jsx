import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../components/Icon';
import { Banner, StatRow } from '../components/Brand';
import bannerImg from '../assets/banners/claims.jpg';
import { fetchClaims, claimTone as tone } from '../api/claims';
import { getCurrentMemberId, session } from '../api/client';

const TL = () => ['Service Completed', 'Claim Submitted', `Approved by ${session.tenantName || 'your insurer'}`, 'Payment Processed'];

export default function Claims() {
  const [claims, setClaims] = useState(null);
  const [sel, setSel] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const memberId = await getCurrentMemberId();
        const list = await fetchClaims(memberId);
        if (cancelled) return;
        setClaims(list);
        setSel(list[0] || null);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load claims from the backend.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const total = claims?.length || 0;
  const approved = claims?.filter((c) => c.status === 'Approved' || c.status === 'Paid').length || 0;
  const inProgress = claims?.filter((c) => c.status === 'In Progress' || c.status === 'Submitted').length || 0;
  const needsAction = claims?.filter((c) => c.status === 'Needs Action').length || 0;

  return (
    <>
      <Banner eyebrow="Claims" title={<>Track your claims,<br />every step of the way.</>} icon="file" script="Your health coverage works for you." image={bannerImg}
        text="View claim details, check status, and get updates on payments for all your healthcare services.">
        <button className="btn primary">View claim summary →</button><Link className="btn" to="/portal/support">Need help with a claim?</Link>
      </Banner>
      <StatRow items={[['file', '', String(total), 'Total Claims', 'All time'], ['check', 'blue', String(approved), 'Approved', 'Ready for payment'], ['clock', 'orange', String(inProgress), 'In Progress', 'Under review'], ['alert', 'orange', String(needsAction), 'Requires Action', 'Additional information needed']]} />
      {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}
      {!error && !claims && <p className="slate">Loading claims…</p>}
      {claims && claims.length === 0 && <p className="slate">No claims yet.</p>}
      {claims && claims.length > 0 && sel && (
        <div className="cols">
          <section className="card">
            <div className="card-head"><h3>Recent Claims</h3></div>
            <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Claim ID</th><th>Service</th><th>Provider</th><th>Date of Service</th><th>Amount</th><th>Status</th></tr></thead>
              <tbody>{claims.map((c) => (
                <tr key={c.id} onClick={() => setSel(c)} style={{ cursor: 'pointer', background: sel.id === c.id ? 'var(--teal-pale)' : undefined }}>
                  <td><Link className="link" to={`/portal/claims/${c.id}`}>{c.id}</Link><small>{c.kind}</small></td>
                  <td><b>{c.svc}</b><small>{c.by}</small></td><td>{c.prov}<small>{c.loc}</small></td><td>{c.date}<small>{c.time}</small></td>
                  <td><b>KES {c.amount.toLocaleString()}</b></td><td><span className={`pill ${tone(c.status)}`}>{c.status}</span></td>
                </tr>
              ))}</tbody>
            </table>
            </div>
          </section>
          <aside className="card">
            <div className="card-head"><div><b>Claim #{sel.id}</b><br /><small className="slate">{sel.svc}</small></div><span className={`pill ${tone(sel.status)}`}>{sel.status}</span></div>
            <small className="slate"><Icon name="cal" /> {sel.date}, {sel.time}</small><br /><small className="slate"><Icon name="pin" /> {sel.prov} • {sel.loc}</small>
            <table className="table" style={{ margin: '10px 0' }}><tbody><tr><td>Consultation Fee</td><td style={{ textAlign: 'right' }}><b>KES {sel.amount.toLocaleString()}</b></td></tr><tr><td>Member Responsibility</td><td style={{ textAlign: 'right' }}><b>KES {sel.member}</b></td></tr></tbody></table>
            <div className="notice ok"><div style={{ flex: 1 }}>Covered by Insurance</div><b>KES {sel.covered.toLocaleString()}</b></div>
            <h3 style={{ margin: '16px 0 10px', fontSize: 13 }}>Claim Timeline</h3>
            <ul className="timeline">{TL().map((t, i) => <li key={t}><i className={i < (sel.status === 'Approved' || sel.status === 'Paid' ? 4 : 2) ? 'done' : ''} /><div><b>{t}</b></div></li>)}</ul>
            <Link className="btn sm block" to={`/portal/claims/${sel.id}`}>View full details</Link>
          </aside>
        </div>
      )}
    </>
  );
}
