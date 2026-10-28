import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../components/Icon';
import { Banner, initials } from '../components/Brand';
import bannerImg from '../assets/banners/dependants.jpg';
import { api, getCurrentMember } from '../api/client';

const age = (dob) => (dob ? Math.floor((Date.now() - new Date(dob)) / 31557600000) : '—');

export default function Dependants() {
  const [dependants, setDependants] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const member = await getCurrentMember();
        const list = await api.getDependants(member.external_ref);
        if (!cancelled) setDependants(list);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load dependants from the backend.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const DEP = dependants || [];
  return (
    <>
      <Banner eyebrow="Your dependants" title={<>Take care of your family.<br /><span style={{ color: 'var(--teal-deep)' }}>Together.</span></>} icon="users" script={'Healthy family,\nbrighter future'} image={bannerImg}
        text="Manage your dependants, view their coverage, and access health services for your loved ones — all in one place.">
        <button className="btn primary">+ Add Dependant</button><button className="btn">View Coverage Details</button>
      </Banner>
      {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}
      {!error && !dependants && <p className="slate">Loading dependants…</p>}
      {dependants && (
      <div className="cols">
        <section className="card">
          <div className="card-head"><div><h3>Your Dependants <span className="pill">{DEP.length} Dependants</span></h3><small className="slate">Manage your family members and their health coverage.</small></div><small className="slate">Sort by: None</small></div>
          {DEP.length === 0 && <p className="slate">No dependants on file.</p>}
          {DEP.map((d) => (
            <div className="rowitem" key={d.id}>
              <span className="avatar" style={{ width: 46, height: 46 }}>{initials(d.full_name)}</span>
              <div className="grow"><b>{d.full_name}</b> <span className="pill">{d.status === 'active' ? 'Active' : d.status}</span><small>{d.relationship_to_principal || '—'} • Age {age(d.date_of_birth)}</small><small className="muted">Ref: {d.external_ref}</small></div>
              <div style={{ width: 150 }}><small className="muted">Coverage</small><b style={{ fontSize: 12 }}><Icon name="shield" /> {d.scheme}</b><small className="muted">{d.plan}</small></div>
              <div style={{ width: 120 }}><small className="muted">Source</small><b style={{ fontSize: 12 }}>{d.source}</b></div>
              <Link className="btn primary sm" to="/portal/dependants">View Details →</Link>
            </div>
          ))}
          <div className="notice ok"><Icon name="shield" /><div style={{ flex: 1 }}><b>Important Information:</b> Keep your dependant information up to date to ensure uninterrupted coverage and seamless access to services.</div><Link className="link" to="/portal/support">Contact Support →</Link></div>
        </section>
        <aside className="stack">
          <section className="card"><div className="card-head"><h3><Icon name="shield" /> Dependants Coverage</h3></div><p className="slate" style={{ fontSize: 11.5, marginBottom: 12 }}>All your dependants are covered under your current plan.</p>
            <div className="grid g2"><div><small className="muted">Plan Type</small><br /><b>Family Plan</b></div><div><small className="muted">Total Dependants</small><br /><b>{DEP.length}</b></div></div></section>
          <section className="card"><div className="card-head"><h3>Quick Actions</h3></div>
            {[['plus', 'Add New Dependant', 'Register a family member'], ['file', 'Update Dependant Details', 'Edit information or change coverage'], ['card', 'Download Dependant Cards', 'Get member cards for your dependants']].map(([i, t, s]) => <button key={t} className="rowitem" style={{ width: '100%', textAlign: 'left' }}><span className="tile-icon"><Icon name={i} /></span><div className="grow"><b>{t}</b><small>{s}</small></div></button>)}</section>
          <section className="promo"><b>Because they matter too.</b><p>Your family's health is part of your health. Ensure optimal coverage with our comprehensive family plans.</p><Link className="btn sm" to="/portal/my-health">View Coverage Details →</Link></section>
        </aside>
      </div>
      )}
    </>
  );
}
