import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Icon from '../components/Icon';
import { initials } from '../components/Brand';

const TABS = ['Overview', 'Consultation Notes', 'Prescription', 'Follow-up'];

export default function AppointmentDetail() {
  const { id } = useParams();
  const [tab, setTab] = useState('Overview');
  return (
    <>
      <Link to="/portal/appointments" className="back"><Icon name="arrow" style={{ transform: 'rotate(180deg)' }} /> Back to Appointments</Link>
      <div className="page-title"><div><h1>Appointment Details <span className="pill">✓ Completed</span></h1><p>View your appointment information, doctor details and next steps.</p></div></div>
      <section className="card">
        <div className="appt" style={{ flexWrap: 'wrap' }}>
          <span className="avatar" style={{ width: 52, height: 52 }}>{initials('Dr. Amina Njoroge')}</span>
          <div className="info"><b>Dr. Amina Njoroge</b><small>General Physician</small><small>Nairobi Health Labs · ★ 4.8 (124 reviews)</small></div>
          <div className="kv kv-2"><div><Icon name="cal" /><span><small>Appointment date</small><b>Oct 8, 2026</b><small>09:30 AM – 10:00 AM</small></span></div><div><Icon name="pin" /><span><small>Location</small><b>Nairobi Health Labs</b><small>Nairobi, Kenya</small></span></div></div>
        </div>
        <div className="notice ok" style={{ marginTop: 14 }}><Icon name="check" /><div><b>STATUS: Completed</b> — Your consultation has been completed.</div></div>
      </section>
      <div className="tabs">{TABS.map((t) => <button key={t} className={tab === t ? 'on' : ''} onClick={() => setTab(t)}>{t}</button>)}</div>
      <div className="cols">
        <div className="stack">
          {tab === 'Overview' && <>
            <section className="card"><h3 style={{ marginBottom: 14 }}>Appointment Overview</h3>
              <div className="kv">
                {[['file', 'Appointment ID', id || 'APT-2026-0084'], ['cal', 'Booked On', 'Oct 6, 2026 • 02:14 PM'], ['hospital', 'Type', 'In-Person Consultation'], ['users', 'Booked Through', 'Member Portal'], ['stetho', 'Reason for Visit', 'General Checkup'], ['card', 'Payment Status', 'Paid · Covered by scheme'], ['clock', 'Duration', '30 minutes'], ['card', 'Amount Paid', 'KES 2,500']].map(([i, l, v]) => <div key={l}><Icon name={i} /><span><small>{l}</small><b>{v}</b></span></div>)}
              </div></section>
            <section className="card"><h3 style={{ marginBottom: 8 }}>Visit Summary</h3><p className="slate" style={{ fontSize: 13 }}>You came in for a general checkup. Your vitals were normal and no immediate concerns were found. The doctor advised you to maintain a healthy lifestyle and come back for a follow-up in 6 months.</p>
              <div className="notice ok" style={{ marginTop: 14, alignItems: 'center' }}><Icon name="check" /><div style={{ flex: 1 }}><b>Next follow-up</b><br />Apr 8, 2027 • 09:30 AM (6 months)</div><button className="btn sm">Book Follow-up</button></div></section>
          </>}
          {tab === 'Consultation Notes' && <section className="card"><h3>Clinical notes</h3><p className="slate" style={{ marginTop: 8 }}>Notes are written by the treating clinician and shared with you once the visit is signed off. BP 118/76, HR 72, temperature 36.6 °C. No acute findings.</p></section>}
          {tab === 'Prescription' && <section className="card"><h3>Prescription</h3><p className="slate" style={{ marginTop: 8 }}>No medication was prescribed at this visit. <Link className="link" to="/portal/prescriptions">View all prescriptions →</Link></p></section>}
          {tab === 'Follow-up' && <section className="card"><h3>Follow-up</h3><p className="slate" style={{ marginTop: 8 }}>Routine review in 6 months (Apr 2027). We'll remind you a week before.</p></section>}
          <section className="card"><div className="card-head"><h3>Related Appointments</h3><Link className="link" to="/portal/appointments">View all →</Link></div><div className="list-row"><div className="datebox"><small>SEP</small><b>26</b></div><div className="grow"><b>Dr. Collins Ochieng</b><small>Orthopedic Surgeon · Completed</small></div></div></section>
        </div>
        <aside className="stack">
          <section className="card"><h3 style={{ marginBottom: 12 }}>Quick Actions</h3><div className="btnstack">
            <Link className="btn primary" to="/portal/find-care">Book Another Appointment</Link><button className="btn">Download Visit Summary</button><Link className="btn" to="/portal/prescriptions">View Prescription</Link><Link className="btn" to="/portal/lab-tests/LT-2026-0084">View Lab Test Results</Link></div></section>
          <section className="card"><h3 style={{ marginBottom: 12 }}>Doctor Information</h3><div className="appt"><span className="avatar">AN</span><div className="info"><b>Dr. Amina Njoroge</b><small>General Physician</small><small>Nairobi Health Labs</small></div></div><button className="btn sm block" style={{ marginTop: 12 }}>View Profile →</button></section>
          <section className="card"><b>Need Assistance?</b><p className="slate" style={{ fontSize: 12, margin: '4px 0 10px' }}>Our support team is here to help you with any questions about your appointment.</p><Link className="btn sm block" to="/portal/support">Contact Support</Link></section>
        </aside>
      </div>
    </>
  );
}
