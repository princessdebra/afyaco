import { useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../components/Icon';
import { Banner, greeting } from '../components/Brand';
import { session } from '../api/client';
import bannerImg from '../assets/banners/my-health.jpg';

const VITALS = [['heart', 'Heart Rate', '72', 'bpm', 'Normal range (60 - 100)'], ['activity', 'Blood Pressure', '118/76', 'mmHg', 'Normal range (<120/80)'], ['activity', 'Temperature', '36.6', '°C', 'Normal range (36 - 37.2)'], ['activity', 'Respiratory Rate', '16', 'bpm', 'Normal range (12 - 20)'], ['activity', 'Weight', '68', 'kg', 'Last updated Oct 8, 2026']];
const RANGES = { '7D': [72, 74, 73, 71, 72, 72, 72], '30D': [75, 74, 73, 74, 72, 73, 72], '3M': [78, 76, 75, 74, 73, 72, 72], '1Y': [80, 79, 77, 75, 74, 73, 72] };
const RECORDS = [['file', 'Medical History', 'View past conditions'], ['shield', 'Allergies', 'Manage your allergies'], ['users', 'Family History', 'View family conditions'], ['shield', 'Immunizations', 'View your vaccination records']];
const GOALS = [['Stay Active', 70], ['Eat Healthy', 55], ['Sleep Better', 80]];

export default function MyHealth() {
  const [rng, setRng] = useState('3M');
  const pts = RANGES[rng].map((v, i) => `${i * 50 + 10},${130 - (v - 60) * 4}`).join(' ');
  return (
    <>
      <Banner eyebrow={`${greeting()}${session.fullName ? `, ${session.fullName.split(' ')[0]}` : ''}`} title={<>Your health, your<br />journey.</>} icon="activity" script={'Take charge of your\nwellness journey'} image={bannerImg}
        text="Track your wellness, stay informed and take control of your health — all in one place.">
        <button className="btn primary">View Health Summary →</button><button className="btn">Update Health Info</button>
      </Banner>
      <section>
        <div className="card-head"><div><h3>Your Vital Signs</h3><p className="slate" style={{ fontSize: 12 }}>Latest recorded values</p></div></div>
        <div className="vitals">{VITALS.map(([i, l, v, u, n]) => <div className="card" key={l}><div className="card-head" style={{ marginBottom: 6 }}><small className="slate">{l}</small><Icon name={i} style={{ color: 'var(--teal-primary)' }} /></div><b>{v}</b> <small style={{ display: 'inline' }}>{u}</small><small>{n}</small></div>)}</div>
      </section>
      <div className="cols">
        <div className="stack">
          <section className="card">
            <div className="card-head"><div><h3>Health Trends</h3><small className="slate">Your health data over time</small></div><div className="chips">{Object.keys(RANGES).map((r) => <button key={r} className={rng === r ? 'on' : ''} onClick={() => setRng(r)}>{r}</button>)}</div></div>
            <svg className="line" viewBox="0 0 320 140" role="img" aria-label={`Heart rate trend, ${rng}`} preserveAspectRatio="none"><polyline fill="none" stroke="var(--teal-primary)" strokeWidth="2.5" points={pts} />{RANGES[rng].map((v, i) => <circle key={i} cx={i * 50 + 10} cy={130 - (v - 60) * 4} r="3.5" fill="var(--teal-primary)" />)}</svg>
            <div className="legend"><span><i style={{ background: 'var(--teal-primary)' }} />Heart Rate</span><span><i style={{ background: 'var(--info-blue)' }} />Blood Pressure (Sys)</span><span><i style={{ background: 'var(--rx-violet)' }} />Weight</span></div>
          </section>
          <section className="card"><div className="card-head"><div><h3>Health Records</h3><small className="slate">Your complete medical history</small></div></div>
            <div className="grid g4">{RECORDS.map(([i, t, s]) => <div className="card" key={t} style={{ padding: 14 }}><span className="tile-icon"><Icon name={i} /></span><b style={{ display: 'block', margin: '8px 0 2px', fontSize: 13 }}>{t}</b><small className="slate">{s}</small></div>)}</div></section>
        </div>
        <aside className="stack">
          <section className="card"><div className="card-head"><h3>Recent Readings</h3></div>{[['Heart Rate', '72 bpm'], ['Blood Pressure', '118/76 mmHg'], ['Weight', '68 kg'], ['Temperature', '36.6 °C']].map(([l, v]) => <div className="list-row" key={l} style={{ padding: '8px 0' }}><div className="grow"><b>{l}</b></div><span>{v}</span></div>)}</section>
          <section className="card"><div className="card-head"><h3>Health Score</h3></div><div style={{ display: 'flex', gap: 16, alignItems: 'center' }}><div className="donut" style={{ '--v': 82 }}><div>82<small>/100</small></div></div><div><b>Your health is on track!</b><p className="slate" style={{ fontSize: 11.5 }}>Keep up the good work with your wellness habits and regular checkups.</p></div></div></section>
          <section className="card"><div className="card-head"><h3>Quick Actions</h3></div><div className="qgrid"><Link to="/portal/find-care"><Icon name="cal" />Book Appointment</Link><Link to="/portal/prescriptions"><Icon name="pill" />View Prescriptions</Link><Link to="/portal/lab-tests"><Icon name="flask" />Order Lab Tests</Link><button><Icon name="activity" />Update Health Info</button></div></section>
          <section className="card"><div className="card-head"><h3>Wellness Goals</h3></div>{GOALS.map(([g, p]) => <div className="meter" key={g}><div className="lbl"><b>{g}</b><span>{p}%</span></div><div className="track"><i style={{ width: `${p}%` }} /></div></div>)}</section>
        </aside>
      </div>
    </>
  );
}
