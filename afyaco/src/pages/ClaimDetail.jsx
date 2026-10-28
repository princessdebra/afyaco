import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Icon from '../components/Icon';
import { fetchClaims } from '../api/claims';
import { getCurrentMemberId, session } from '../api/client';

const TL = () => [['Claim Submitted', '', `Your claim was received by ${session.tenantName || 'your insurer'}.`], ['Under Review', '', 'We verified your details and documents.'], ['Approved', '', 'Your claim has been approved.'], ['Payment Processed', '', 'The amount has been sent to your account.']];

export default function ClaimDetail() {
  const { id } = useParams();
  const [claims, setClaims] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const memberId = await getCurrentMemberId();
        const list = await fetchClaims(memberId);
        if (!cancelled) setClaims(list);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load claim from the backend.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (error) return <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>;
  if (!claims) return <p className="slate">Loading claim…</p>;

  const c = claims.find((x) => x.id === id) || claims[0];
  if (!c) return <p className="slate">Claim not found.</p>;

  return (
    <>
      <Link to="/portal/claims" className="back"><Icon name="arrow" style={{ transform: 'rotate(180deg)' }} /> Back to Claims</Link>
      <div className="page-title"><div><h1>Claim Details</h1><p>View the full details of your claim, including service, provider, amount and status.</p></div><div><small className="muted">Claim #{c.id}</small> <span className="pill">{c.status}</span></div></div>
      <div className="cols">
        <div className="stack">
          <div className="notice ok" style={{ alignItems: 'center' }}><Icon name="shield" /><div style={{ flex: 1 }}><b>Claim status: {c.status}</b><br />Amounts reflect what {session.tenantName || 'your insurer'} has recorded for this claim.</div><button className="btn sm"><Icon name="file" /> Download Claim Summary</button></div>
          <section className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap' }}>
              <div className="appt"><span className="tile-icon"><Icon name="stetho" /></span><div className="info"><b>{c.svc}</b><small>Provider: {c.by}</small><small>{c.prov}</small></div></div>
              <div className="amount"><small className="muted">Total Amount <span className="pill">Covered by Insurance</span></small><b>KES {c.amount.toLocaleString()}</b><small className="muted">Member Responsibility KES {c.member} (Co-pay)</small></div>
            </div>
            <div className="grid g3" style={{ marginTop: 16 }}>
              {[['cal', 'Date of Service', `${c.date}`, c.time], ['pin', 'Provider', c.prov, c.loc], ['file', 'Service Type', c.kind, '']].map(([i, l, v, s]) => <div className="card" key={l} style={{ padding: 12, display: 'flex', gap: 10 }}><Icon name={i} className="muted" /><div><small className="muted">{l}</small><br /><b style={{ fontSize: 12.5 }}>{v}</b><br /><small className="slate">{s}</small></div></div>)}
            </div>
          </section>
          <section className="card"><h3 style={{ marginBottom: 8 }}>Claim Breakdown</h3>
            <div className="table-wrap"><table className="table"><thead><tr><th>Description</th><th>Amount (KES)</th><th>Insurance Covered (KES)</th><th>Member Pays (KES)</th></tr></thead>
              <tbody><tr className="total"><td>{c.svc}</td><td>{c.amount.toLocaleString()}</td><td className="cr">{c.covered.toLocaleString()}</td><td>{c.member}</td></tr></tbody></table></div></section>
          <section className="card"><h3 style={{ marginBottom: 12 }}>Provider Details</h3><div className="kv"><div><Icon name="hospital" /><span><small>Facility</small><b>{c.prov}</b></span></div><div><Icon name="shield" /><span><small>Network status</small><b>In-Network ({session.tenantName || 'your insurer'} panel)</b></span></div><div><Icon name="file" /><span><small>Claim reference</small><b>{c.id}</b></span></div></div></section>
        </div>
        <aside className="stack">
          <section className="card"><h3 style={{ marginBottom: 12 }}>Claim Status Timeline</h3><ul className="timeline">{TL().map(([t, d, s]) => <li key={t}><i className="done" /><div><b>{t}</b><small>{d}</small><small>{s}</small></div></li>)}</ul></section>
          <section className="card"><b>Need help with this claim?</b><p className="slate" style={{ fontSize: 12, margin: '4px 0 10px' }}>Our support team is here to help you with any questions or concerns.</p><Link className="btn sm block" to="/portal/support">Contact Support →</Link></section>
          <section className="card"><div className="card-head"><h3>Related Claims</h3><Link className="link" to="/portal/claims">View all →</Link></div>
            {claims.filter((x) => x.id !== c.id).slice(0, 3).map((x) => <Link to={`/portal/claims/${x.id}`} className="list-row" key={x.id} style={{ padding: '10px 0' }}><div className="grow"><b>{x.id}</b><small>{x.kind} · KES {x.amount.toLocaleString()}</small></div><span className="pill gray">{x.status}</span></Link>)}</section>
        </aside>
      </div>
    </>
  );
}
