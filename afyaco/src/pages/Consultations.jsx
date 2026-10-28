import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Icon from '../components/Icon';
import { Banner, initials } from '../components/Brand';
import bannerImg from '../assets/banners/consultations.jpg';
import { api, getCurrentMemberId } from '../api/client';
import { fetchAppointments } from '../api/appointments';
import RescheduleModal from '../components/RescheduleModal';

const FEAT_KEYS = ['video', 'chat', 'followup', 'history'];
const FEATS = [['video', '', 'Video Consultation', 'See a doctor in real time'], ['chat', 'violet', 'Chat Consultation', 'Get quick text-based advice'], ['users', 'blue', 'Follow-up Care', 'Track your recovery'], ['file', 'green', 'View History', 'Access past consultations']];
const CHECKS = ['Identity confirmed', 'Current location shared', 'Telemedicine consent given', 'Remote-care limitations understood'];

export default function Consultations() {
  const [tab, setTab] = useState('Upcoming');
  const [ok, setOk] = useState([true, true, false, false]);
  const [appts, setAppts] = useState(null);
  const [error, setError] = useState('');
  const [rescheduling, setRescheduling] = useState(false);
  const [showReschedule, setShowReschedule] = useState(false);
  const [unreadChatCount, setUnreadChatCount] = useState(0);
  const ready = ok.every(Boolean);
  const navigate = useNavigate();

  async function load() {
    try {
      const memberId = await getCurrentMemberId();
      setAppts(await fetchAppointments(memberId));
    } catch (err) {
      setError(err.message || 'Could not load consultations from the backend.');
    }
  }
  useEffect(() => {
    load();
    api.listMyConversations()
      .then((cs) => setUnreadChatCount(cs.reduce((sum, c) => sum + c.unread_count, 0)))
      .catch(() => {});
  }, []);

  const telemedUpcoming = (appts?.upcoming || []).filter((a) => a.type === 'Virtual');
  const next = telemedUpcoming[0];
  const past = (appts?.past || []).filter((a) => a.type === 'Virtual' || a.status === 'cancelled');

  function handleJoin() {
    if (next) navigate(`/portal/call/${next.id}`);
    else navigate('/portal/find-care?category=telemedicine');
  }

  function handleChat() {
    if (next) navigate(`/portal/chat/${next.id}`);
    else navigate('/portal/find-care?category=telemedicine');
  }

  function handleFollowUp() {
    navigate('/portal/appointments');
  }

  function handleViewHistory() {
    setTab('Past Consultations');
  }

  async function confirmReschedule(iso) {
    if (!next) return;
    setRescheduling(true);
    try {
      await api.rescheduleAppointment(next.id, iso);
      setShowReschedule(false);
      await load();
    } catch (err) {
      setError(err.message || 'Could not reschedule this consultation.');
    } finally {
      setRescheduling(false);
    }
  }

  return (
    <>
      <Banner eyebrow="Consultations" title={<>Speak to a doctor,<br />anytime, anywhere.</>} icon="video" script="Your health matters." image={bannerImg}
        text="Get expert medical advice through secure video or chat consultations. Our licensed doctors are here to help you and your family.">
        <Link className="btn primary" to="/portal/find-care">Start a new consultation →</Link><Link className="btn" to="/portal/appointments">Book an appointment</Link>
      </Banner>
      <div className="cat cat-4">
        {FEATS.map(([i, t, h, p], idx) => (
          <button type="button" key={h} className="card" style={{ display: 'flex', gap: 12, alignItems: 'center', padding: 14, textAlign: 'left', cursor: 'pointer' }}
            onClick={() => ({ video: handleJoin, chat: handleChat, followup: handleFollowUp, history: handleViewHistory }[FEAT_KEYS[idx]]())}>
            <span className={`tile-icon ${t}`}><Icon name={i} /></span><div style={{ flex: 1 }}><b style={{ fontSize: 13 }}>{h}</b><p className="slate" style={{ fontSize: 11 }}>{p}</p></div>
            {FEAT_KEYS[idx] === 'chat' && unreadChatCount > 0 && <span className="badge-count">{unreadChatCount}</span>}
          </button>
        ))}
      </div>
      {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}
      <div className="cols">
        <div className="stack">
          <section className="card">
            <div className="card-head"><h3>Your Consultations</h3></div>
            <div className="tabs">{['Upcoming', 'Past Consultations', 'Cancelled'].map((t) => <button key={t} className={tab === t ? 'on' : ''} onClick={() => setTab(t)}>{t}</button>)}</div>
            {tab === 'Upcoming' && (
              next ? (
                <div className="rowitem" style={{ background: 'var(--teal-pale)' }}>
                  <div className="datebox"><small>{next.m}</small><b>{next.d}</b><small>{next.t}</small></div>
                  <span className="avatar">{initials(next.doc)}</span>
                  <div className="grow"><b>{next.doc}</b><small>{next.spec} · {next.place}</small><span className="pill violet">Video Consultation</span> <span className="pill">{next.note}</span></div>
                  <button className="btn primary sm" disabled={!ready} style={!ready ? { opacity: .5 } : null} onClick={handleJoin}>
                    <Icon name="video" /> Join Call
                  </button>
                  <button className="btn sm" onClick={() => setShowReschedule(true)}>Reschedule</button>
                </div>
              ) : <p className="slate" style={{ padding: 20 }}>{appts ? 'No upcoming video consultations.' : 'Loading…'}</p>
            )}
            {showReschedule && (
              <RescheduleModal
                title="Reschedule consultation"
                busy={rescheduling}
                onConfirm={confirmReschedule}
                onClose={() => setShowReschedule(false)}
              />
            )}
            {tab !== 'Upcoming' && (
              past.filter((a) => tab === 'Cancelled' ? a.status === 'cancelled' : a.status !== 'cancelled').length === 0
                ? <p className="slate" style={{ padding: 20 }}>Nothing here yet.</p>
                : past.filter((a) => tab === 'Cancelled' ? a.status === 'cancelled' : a.status !== 'cancelled').map((a) => (
                  <div className="list-row" key={a.id}><small className="slate" style={{ width: 90 }}>{a.m} {a.d}</small><span className="avatar">{initials(a.doc)}</span><div className="grow"><b>{a.doc}</b><small>{a.spec} · {a.place}</small></div><span className="pill gray">{a.type}</span><span className={`pill ${a.status === 'cancelled' ? 'red' : ''}`}>{a.note}</span></div>
                ))
            )}
          </section>
        </div>
        <aside className="stack">
          <section className="card"><div className="card-head"><h3>Before you join</h3></div>
            {CHECKS.map((c, i) => <label className="check" key={c}><input type="checkbox" checked={ok[i]} onChange={() => setOk(ok.map((v, j) => (j === i ? !v : v)))} /> {c}</label>)}
            <p className="muted" style={{ fontSize: 10.5, marginTop: 8 }}>Sessions are not recorded by default. Your clinician may refer you to an in-person exam.</p></section>
          <section className="card"><div className="card-head"><h3>Quick Actions</h3></div>
            <div className="qgrid"><Link to="/portal/appointments"><Icon name="cal" />Book Appointment</Link><Link to="/portal/find-care"><Icon name="users" />Find a Doctor</Link><Link to="/portal/find-care"><Icon name="video" />Start Video Call</Link><Link to="/portal/prescriptions"><Icon name="pill" />View Prescriptions</Link></div></section>
          <section className="card" style={{ background: 'var(--teal-pale)' }}><b>Need immediate care?</b><p className="slate" style={{ fontSize: 12, margin: '4px 0 10px' }}>Not feeling well? Get quick medical advice from a doctor now.</p><Link className="btn primary sm block" to="/portal/find-care">Start a Video Consultation →</Link></section>
          <section className="card"><b>Your care is covered</b><p className="slate" style={{ fontSize: 12, margin: '4px 0 8px' }}>Check your benefits and coverage for this consultation.</p><Link className="link" to="/portal/my-health">View Benefits →</Link></section>
          <div className="notice"><Icon name="alert" /><div>In an emergency call <b>0800 720 000</b> — don't wait for a video visit.</div></div>
        </aside>
      </div>
    </>
  );
}
