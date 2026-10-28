import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Icon from '../components/Icon';
import { Banner, StatRow } from '../components/Brand';
import bannerImg from '../assets/banners/appointments.jpg';
import { fetchAppointments } from '../api/appointments';
import { api, getCurrentMemberId } from '../api/client';
import RescheduleModal from '../components/RescheduleModal';

const Row = ({ a, past, onCancel, onReschedule, onJoin, cancelling, rescheduling }) => (
  <div className="list-row">
    <div className="datebox"><small>{a.m}</small><b>{a.d}</b><small>{a.year}</small></div>
    <div className="grow"><b>{a.doc}</b><small>{a.spec} · <Icon name="pin" /> {a.place}</small><small>{a.t}</small></div>
    <span className={`pill ${a.type === 'Virtual' ? 'violet' : 'blue'}`}>{a.type}</span>
    <small className="slate" style={{ width: 130 }}>{a.note}</small>
    <div className="row-actions">
      {a.type === 'Virtual' && !past ? <button className="btn primary sm" onClick={() => onJoin(a)}><Icon name="video" /> Join Call</button> : <Link className="btn primary sm" to={`/portal/appointments/${a.id}`}>View Details</Link>}
      {!past && a.status !== 'cancelled' && (
        <>
          <button className="btn sm" disabled={rescheduling} onClick={() => onReschedule(a.id)}>{rescheduling ? 'Rescheduling…' : 'Reschedule'}</button>
          <button className="btn sm" disabled={cancelling} onClick={() => onCancel(a.id)}>{cancelling ? 'Cancelling…' : 'Cancel'}</button>
        </>
      )}
    </div>
  </div>
);

function buildMonthGrid(year, month) {
  const first = new Date(year, month, 1);
  const start = new Date(first);
  start.setDate(first.getDate() - first.getDay());
  const weeks = [];
  const cursor = new Date(start);
  for (let w = 0; w < 6; w++) {
    const week = [];
    for (let d = 0; d < 7; d++) {
      week.push(new Date(cursor));
      cursor.setDate(cursor.getDate() + 1);
    }
    weeks.push(week);
  }
  return weeks;
}

const dateKey = (d) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;

function Calendar({ appointments }) {
  const today = new Date();
  const [viewDate, setViewDate] = useState(new Date(today.getFullYear(), today.getMonth(), 1));
  const [hovered, setHovered] = useState(null); // { key, appts }
  const weeks = buildMonthGrid(viewDate.getFullYear(), viewDate.getMonth());

  const byDate = new Map();
  for (const a of appointments) {
    const key = dateKey(a.scheduledAt);
    if (!byDate.has(key)) byDate.set(key, []);
    byDate.get(key).push(a);
  }

  return (
    <section className="card">
      <div className="card-head">
        <h3>{viewDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</h3>
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="btn sm" style={{ height: 26, padding: '0 8px' }} onClick={() => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1))}>‹</button>
          <button className="btn sm" style={{ height: 26, padding: '0 8px' }} onClick={() => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1))}>›</button>
        </div>
      </div>
      <table className="calendar">
        <thead><tr>{['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map((d) => <th key={d}>{d}</th>)}</tr></thead>
        <tbody>
          {weeks.map((week, i) => (
            <tr key={i}>
              {week.map((d, j) => {
                const key = dateKey(d);
                const dayAppts = byDate.get(key) || [];
                const isToday = dateKey(today) === key;
                const inMonth = d.getMonth() === viewDate.getMonth();
                return (
                  <td
                    key={j}
                    className={!inMonth ? 'off' : isToday ? 'today' : dayAppts.length ? 'appt' : ''}
                    style={{ position: 'relative' }}
                    onMouseEnter={() => dayAppts.length && setHovered({ key, appts: dayAppts })}
                    onMouseLeave={() => setHovered((h) => (h?.key === key ? null : h))}
                    onFocus={() => dayAppts.length && setHovered({ key, appts: dayAppts })}
                    onBlur={() => setHovered((h) => (h?.key === key ? null : h))}
                    tabIndex={dayAppts.length ? 0 : undefined}
                  >
                    <span>{d.getDate()}</span>
                    {hovered?.key === key && (
                      <div className="card daytip" role="tooltip">
                        {hovered.appts.map((a) => (
                          <div key={a.id} className="daytip-row">
                            <b>{a.doc}</b>
                            <small>{a.type === 'Virtual' ? 'Online' : 'In-person'} · {a.t}</small>
                          </div>
                        ))}
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default function Appointments() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [cancellingId, setCancellingId] = useState(null);
  const [reschedulingId, setReschedulingId] = useState(null);
  const [reschedulingTarget, setReschedulingTarget] = useState(null);
  const navigate = useNavigate();

  async function load() {
    try {
      const memberId = await getCurrentMemberId();
      const result = await fetchAppointments(memberId);
      setData(result);
    } catch (err) {
      setError(err.message || 'Could not load appointments from the backend.');
    }
  }

  useEffect(() => { load(); }, []);

  async function handleCancel(id) {
    if (!window.confirm('Cancel this appointment? This cannot be undone.')) return;
    setCancellingId(id);
    setError('');
    try {
      await api.cancelAppointment(id);
      await load();
    } catch (err) {
      setError(err.message || 'Could not cancel this appointment.');
    } finally {
      setCancellingId(null);
    }
  }

  async function confirmReschedule(iso) {
    setReschedulingId(reschedulingTarget);
    setError('');
    try {
      await api.rescheduleAppointment(reschedulingTarget, iso);
      setReschedulingTarget(null);
      await load();
    } catch (err) {
      setError(err.message || 'Could not reschedule this appointment.');
    } finally {
      setReschedulingId(null);
    }
  }

  function handleJoin(a) {
    navigate(`/portal/call/${a.id}`);
  }

  const upcoming = data?.upcoming || [];
  const past = data?.past || [];

  return (
    <>
      <Banner eyebrow="Appointments" title={<>Manage your appointments,<br />your health, your way.</>} icon="cal" script={'Better appointments,\nHealthier tomorrow'} image={bannerImg}
        text="Book, reschedule or cancel appointments with verified doctors, hospitals and specialists — all in one place.">
        <Link className="btn primary" to="/portal/find-care">Book Now Appointment →</Link><Link className="btn" to="/portal/find-care">Find a Doctor</Link>
      </Banner>
      <StatRow items={[['cal', '', String(upcoming.length), 'Upcoming Appointments', upcoming[0] ? `Next: ${upcoming[0].doc}` : ''], ['clock', 'violet', String(past.length), 'Past Appointments', 'View your history'], ['clock', 'blue', String(upcoming.filter((a) => a.status === 'requested').length), 'Pending Confirmation', 'Awaiting your doctor'], ['users', 'green', String(new Set([...upcoming, ...past].map((a) => a.doc)).size), 'Your Doctors', 'View all your healthcare providers']]} />
      {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}
      {!error && !data && <p className="slate">Loading appointments…</p>}
      {reschedulingTarget && (
        <RescheduleModal
          title="Reschedule appointment"
          busy={reschedulingId === reschedulingTarget}
          onConfirm={confirmReschedule}
          onClose={() => setReschedulingTarget(null)}
        />
      )}
      {data && (
      <div className="cols">
        <div className="stack">
          <section className="card"><div className="card-head"><h3>Upcoming Appointments</h3></div>{upcoming.length ? upcoming.map((a) => <Row key={a.id} a={a} onCancel={handleCancel} onReschedule={setReschedulingTarget} onJoin={handleJoin} cancelling={cancellingId === a.id} rescheduling={reschedulingId === a.id} />) : <p className="slate">No upcoming appointments.</p>}</section>
          <section className="card"><div className="card-head"><h3>Past Appointments</h3></div>{past.length ? past.map((a) => <Row key={a.id} a={a} past />) : <p className="slate">No past appointments.</p>}</section>
        </div>
        <aside className="stack">
          <Calendar appointments={[...upcoming, ...past]} />
          <section className="card"><div className="card-head"><h3>Quick Actions</h3></div>
            <div className="qgrid">
              <Link to="/portal/find-care"><Icon name="cal" />Book Appointment</Link><Link to="/portal/find-care"><Icon name="users" />Find a Doctor</Link>
              <Link to="/portal/support"><Icon name="phone" />Contact Support</Link>
            </div>
          </section>
          <div className="notice info"><Icon name="alert" /><div>If eligibility can't be confirmed we hold your slot and queue verification — cover is never assumed.</div></div>
        </aside>
      </div>
      )}
    </>
  );
}
