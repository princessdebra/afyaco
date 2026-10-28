import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../components/Icon';
import { Banner, greeting } from '../components/Brand';
import { appointments, activity } from '../data/mock';
import { api, getCurrentMember } from '../api/client';
import bannerImg from '../assets/banners/dashboard.jpg';

const QA = [
  ['stetho', '', 'Consult a Doctor', 'See a GP or specialist via video or in person.', '/portal/find-care'],
  ['pill', 'violet', 'Get a Prescription', 'Order and refill your medication.', '/portal/prescriptions'],
  ['flask', 'blue', 'Book a Lab Test', 'Book a laboratory and book your test.', '/portal/lab-tests'],
  ['hospital', 'orange', 'Find a Hospital', 'View our network of hospitals and facilities.', '/portal/find-care'],
  ['file', 'green', 'Check Claims', 'Track your claims and view status updates.', '/portal/claims'],
];
const BARS = [[40, 20, 10], [60, 24, 14], [34, 20, 8], [80, 30, 20], [56, 24, 12], [72, 28, 16]];

const BENEFIT_LABEL = { outpatient: 'Outpatient Cover', inpatient: 'Inpatient Cover' };
const BENEFIT_TONE = { outpatient: 'blue', inpatient: '' };
const parseAmount = (s) => Number(String(s).replace(/[^0-9.]/g, '')) || 0;

export default function Dashboard() {
  const next = appointments[0]; // still mock — no "my appointments" summary endpoint yet
  const [member, setMember] = useState(null);
  const [benefits, setBenefits] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const memberData = await getCurrentMember();
        const benefitData = await api.getMemberBenefits(memberData.external_ref);
        if (cancelled) return;
        setMember(memberData);
        setBenefits(
          benefitData.map((b) => {
            const used = parseAmount(b.used_amount);
            const limit = parseAmount(b.limit_amount);
            return {
              name: BENEFIT_LABEL[b.benefit] || b.benefit,
              used: b.used_amount,
              limit: b.limit_amount,
              pct: limit ? Math.round((used / limit) * 100) : 0,
              left: `${limit ? Math.round(100 - (used / limit) * 100) : 0}% remaining`,
              tone: BENEFIT_TONE[b.benefit] || '',
            };
          })
        );
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load member data from the backend.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <>
      <Banner eyebrow={`${greeting()}${member ? `, ${member.full_name.split(' ')[0].toUpperCase()}` : ''}`} title="Your health matters."
        text="Access quality care, manage your benefits, and stay on top of your health — all in one place." script={'Better care.\nA healthier you.'} image={bannerImg}>
        <Link className="btn primary" to="/portal/find-care"><Icon name="cal" /> Book a consultation</Link>
        <Link className="btn" to="/portal/my-health">Check my benefits</Link>
      </Banner>

      <div className="grid g5">
        {QA.map(([i, t, h, p, to]) => (
          <Link key={h} to={to} className="card qa"><span className={`tile-icon ${t}`}><Icon name={i} /></span><b>{h}</b><p>{p}</p></Link>
        ))}
      </div>

      <div className="cols">
        <div className="stack">
          <section className="card">
            <div className="card-head"><h3>Upcoming Appointments</h3><Link className="link" to="/portal/appointments">View all →</Link></div>
            <div className="appt">
              <span className="photo">AN</span>
              <div className="info"><span className="pill blue">{next.mode}</span><br /><b>{next.doctor}</b><small>{next.spec}</small><small><Icon name="clock" /> {next.when} · {next.place}</small></div>
              <Link className="btn primary sm" to="/portal/consultations"><Icon name="video" /> Join call</Link>
            </div>
          </section>

          <section>
            <div className="card-head"><h3>Your Health Summary</h3><Link className="link" to="/portal/my-health">View details →</Link></div>
            <div className="grid g4">
              {[['heart', 'Overall Health', 'Good', 'Keep up the great work!', ''], ['shield', 'Active Benefits', 'Medical Scheme', '5.2 months · Annual limit', 'blue'], ['pill', 'Current Medications', '2 active', 'View prescriptions →', 'violet'], ['flask', 'Recent Lab Results', '1 new result', 'View results →', 'orange']].map(([i, t, l, v, n]) => (
                <div className="card stat" key={l}><span className={`tile-icon ${t}`}><Icon name={i} /></span><small>{l}</small><b style={{ fontSize: 14 }}>{v}</b><small className="muted">{n}</small></div>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="card-head"><div><h3>Health &amp; Wellness Analytics <span className="pill gray">Updated today</span></h3><p className="slate" style={{ fontSize: 12 }}>Personal biometrics, preventive check milestones &amp; 6-month claim spending</p></div><button className="btn sm">Export report</button></div>
            <div className="grid g4" style={{ marginBottom: 18 }}>
              {[['Blood Pressure', '118/76', 'Optimal'], ['Fasting Glucose', '5.2', 'Normal range'], ['Body Mass (BMI)', '23.4', 'Healthy weight'], ['Wellness Score', '88', 'Top tier']].map(([l, v, s]) => (
                <div key={l} className="card" style={{ padding: 12 }}><small className="slate">{l}</small><br /><b style={{ fontSize: 18 }}>{v}</b><br /><span className="pill">{s}</span></div>
              ))}
            </div>
            <small className="slate"><b>6-Month Claim Spending</b></small>
            <div className="bars" role="img" aria-label="Six month claim spending chart">
              {BARS.map(([a, b, c], i) => (
                <div key={i}><span className="dx" style={{ height: c }} /><span className="rx" style={{ height: b }} /><span className="gp" style={{ height: a }} />{['May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct'][i]}</div>
              ))}
            </div>
            <div className="legend"><span><i style={{ background: 'var(--teal-deep)' }} />GP &amp; Specialist</span><span><i style={{ background: 'var(--rx-violet)' }} />Pharmacy</span><span><i style={{ background: 'var(--warn-orange)' }} />Diagnostics</span></div>
          </section>
        </div>

        <aside className="stack">
          <section className="card">
            <div className="card-head"><h3>Insurance Cover &amp; Policies</h3><span className="pill">Active</span></div>
            {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)', fontSize: 11 }}>{error}</p>}
            {!error && !member && <p className="slate" style={{ fontSize: 11 }}>Loading member data…</p>}
            {member && (
              <>
                <p className="slate" style={{ fontSize: 11 }}>{member.plan} · {member.is_principal ? 'Principal' : 'Dependant'}</p>
                <div className="notice ok" style={{ margin: '12px 0' }}><Icon name="shield" /><div><b>{member.scheme}</b><br />Principal: {member.full_name}</div></div>
              </>
            )}
            {benefits.map((b) => (
              <div className="meter" key={b.name}><div className="lbl"><b>{b.name}</b><span>{b.limit}</span></div><div className="track"><i className={b.tone} style={{ width: `${b.pct}%` }} /></div><small className="muted">{b.used} used · {b.left}</small></div>
            ))}
            {member && <p className="muted" style={{ fontSize: 10.5, marginTop: 10 }}>Source: {member.source} · {new Date(member.retrieved_at).toLocaleString()}</p>}
          </section>
          <section className="card">
            <div className="card-head"><h3>Recent Activity</h3></div>
            <ul className="act">{activity.map(([i, t, s, c]) => (<li key={t}><span className={`tile-icon ${c}`}><Icon name={i} /></span><div><b>{t}</b><small>{s}</small></div></li>))}</ul>
          </section>
          <section className="promo"><b>Need to see a specialist?</b><p>Get expert care from our trusted network of specialists and facilities.</p><Link className="btn sm" to="/portal/find-care">Explore providers →</Link></section>
        </aside>
      </div>
    </>
  );
}
