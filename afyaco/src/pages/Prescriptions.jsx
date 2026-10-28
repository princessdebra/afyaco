import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../components/Icon';
import { Banner, StatRow } from '../components/Brand';
import bannerImg from '../assets/banners/prescriptions.jpg';
import { fetchPrescriptions } from '../api/recommendations';
import { api, getCurrentMemberId } from '../api/client';
import InfoModal from '../components/InfoModal';

export default function Prescriptions() {
  const [tab, setTab] = useState('Active');
  const [on, setOn] = useState({ 0: true, 1: true, 2: true });
  const [rx, setRx] = useState(null);
  const [error, setError] = useState('');
  const [refillingId, setRefillingId] = useState(null);
  const [refilled, setRefilled] = useState(false);

  async function load() {
    try {
      const memberId = await getCurrentMemberId();
      setRx(await fetchPrescriptions(memberId));
    } catch (err) {
      setError(err.message || 'Could not load prescriptions from the backend.');
    }
  }

  useEffect(() => { load(); }, []);

  async function handleRefill(id) {
    if (!id) {
      setError('No active prescription to refill.');
      return;
    }
    setRefillingId(id);
    setError('');
    try {
      await api.refillPrescription(id);
      await load();
      setRefilled(true);
    } catch (err) {
      setError(err.message || 'Could not request this refill.');
    } finally {
      setRefillingId(null);
    }
  }

  const all = rx || [];
  const rows = all.filter((r) => tab === 'All' || r.status === tab);
  const activeCount = all.filter((r) => r.status === 'Active').length;
  const completedCount = all.filter((r) => r.status === 'Completed').length;
  const REM = all.filter((r) => r.status === 'Active').slice(0, 3).map((r) => r.name);
  return (
    <>
      {refilled && (
        <InfoModal
          icon="pill"
          title="Refill requested"
          message="Your pharmacy has been notified and will prepare your medication."
          onClose={() => setRefilled(false)}
        />
      )}
      <Banner eyebrow="Prescriptions" title={<>Your medications,<br />made simple.</>} icon="pill" script={'Take care of your health,\none prescription at a time.'} image={bannerImg}
        text="View, manage and refill your prescriptions. Get reminders and track your medication, all in one place.">
        <button className="btn primary" disabled title="New prescriptions require a clinician — book a consultation first">Request a Prescription →</button>
        <button className="btn" disabled={!all.some((r) => r.status === 'Active') || !!refillingId} onClick={() => handleRefill(all.find((r) => r.status === 'Active')?.id)}>{refillingId ? 'Requesting…' : 'Refill a Prescription'}</button>
      </Banner>
      <StatRow items={[['pill', '', String(activeCount), 'Active Prescriptions', 'Currently being taken'], ['check', 'violet', String(completedCount), 'Completed Prescriptions', 'Finished in the last 3 months'], ['clock', 'blue', '0', 'Refill Due Soon', 'Within 7 days'], ['file', 'orange', '0', 'Pending Requests', 'Awaiting approval']]} />
      {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}
      {!error && !rx && <p className="slate">Loading prescriptions…</p>}
      {rx && (
      <div className="cols">
        <section className="card">
          <div className="card-head"><h3>Your Prescriptions</h3><small className="slate">Sort by: Newest</small></div>
          <div className="tabs">{[['Active', activeCount], ['Completed', completedCount], ['All', all.length]].map(([t, n]) => <button key={t} className={tab === t ? 'on' : ''} onClick={() => setTab(t)}>{t} ({n})</button>)}</div>
          {rows.length === 0 && <p className="slate">No prescriptions in this view.</p>}
          {rows.map((r) => (
            <div className="list-row" key={r.id}>
              <span className="tile-icon violet"><Icon name="pill" /></span>
              <div className="grow"><b>{r.name}</b><small>{r.form}</small><small>Prescribed by {r.by} • {r.date}</small></div>
              <div style={{ textAlign: 'right' }}><span className={`pill ${r.status === 'Active' ? '' : 'gray'}`}>{r.status}</span><small className="muted">{r.refills}</small><small className="muted">Auth: {r.auth}</small></div>
              {r.status === 'Active' ? <button className="btn sm" disabled={refillingId === r.id} onClick={() => handleRefill(r.id)}>{refillingId === r.id ? 'Requesting…' : '↻ Request Refill'}</button> : <small className="muted">Dispensed</small>}
            </div>
          ))}
        </section>
        <aside className="stack">
          <section className="card"><div className="card-head"><h3>Quick Actions</h3></div>
            <div className="qgrid">
              <button disabled title="New prescriptions require a clinician — book a consultation first"><Icon name="plus" />Request Prescription<small>Get a new prescription</small></button>
              <button disabled={!all.some((r) => r.status === 'Active') || refillingId} onClick={() => handleRefill(all.find((r) => r.status === 'Active')?.id)}><Icon name="activity" />Refill Prescription<small>Order your medication</small></button>
              <Link to="/portal/find-care"><Icon name="pill" />View Pharmacy<small>Panel pharmacies</small></Link>
              <Link to="/portal/support"><Icon name="file" />Medication Guide<small>Learn about your medication</small></Link>
            </div></section>
          <section className="card"><div className="card-head"><h3><Icon name="bell" /> Medication Reminders</h3></div>
            {REM.map((r, i) => <div className="list-row" key={r} style={{ padding: '10px 0' }}><div className="grow"><b>{r}</b><small>08:00 AM • Daily</small></div><input type="checkbox" className="switch" checked={!!on[i]} onChange={() => setOn({ ...on, [i]: !on[i] })} aria-label={`Reminder for ${r}`} /></div>)}</section>
          <section className="card" style={{ background: 'var(--teal-pale)' }}><b>Need a prescription renewal?</b><p className="slate" style={{ fontSize: 12, margin: '4px 0 10px' }}>Easily request a renewal for your ongoing medication.</p><button className="btn primary sm" disabled={!all.some((r) => r.status === 'Active') || refillingId} onClick={() => handleRefill(all.find((r) => r.status === 'Active')?.id)}>Request Renewal →</button></section>
          <div className="notice info"><Icon name="shield" /><div>Pharmacies handle stock and substitutions; you'll approve any substitution first.</div></div>
        </aside>
      </div>
      )}
    </>
  );
}
