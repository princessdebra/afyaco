import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../../components/Icon';
import { initials } from '../../components/Brand';
import { api, session } from '../../api/client';

function isToday(iso) {
  const d = new Date(iso);
  const n = new Date();
  return d.toDateString() === n.toDateString();
}

function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

export default function ProviderDashboard() {
  const [pending, setPending] = useState(null);
  const [confirmed, setConfirmed] = useState(null);
  const [members, setMembers] = useState({});
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [p, c] = await Promise.all([api.listPendingAppointments(), api.listMyProviderAppointments()]);
        if (cancelled) return;
        setPending(p);
        setConfirmed(c);
        const todays = c.filter((a) => isToday(a.scheduled_at));
        const ids = [...new Set(todays.map((a) => a.member_id))];
        const fetched = await Promise.all(ids.map((id) => api.getMemberById(id).catch(() => null)));
        if (cancelled) return;
        const next = {};
        ids.forEach((id, i) => { if (fetched[i]) next[id] = fetched[i]; });
        setMembers(next);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load your dashboard.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const todaysAppts = (confirmed || []).filter((a) => isToday(a.scheduled_at)).sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at));

  return (
    <>
      <div className="page-title"><div><h1>Welcome back, {session.fullName || 'Doctor'}</h1><p>{session.tenantName || 'Your organisation'} · {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}</p></div></div>
      {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}
      <div className="statrow">
        <div className="card"><span className="tile-icon orange"><Icon name="clock" /></span><div><b>{pending ? pending.length : '—'}</b><small>Pending Approval</small><small>Needs your response</small></div></div>
        <div className="card"><span className="tile-icon"><Icon name="cal" /></span><div><b>{todaysAppts.length}</b><small>Today's Appointments</small><small>Confirmed for today</small></div></div>
        <div className="card"><span className="tile-icon blue"><Icon name="users" /></span><div><b>{confirmed ? new Set(confirmed.map((a) => a.member_id)).size : '—'}</b><small>Patients</small><small>With a confirmed visit</small></div></div>
      </div>

      <div className="cols">
        <section className="card">
          <div className="card-head"><h3>Today's Schedule</h3><Link className="link" to="/provider/appointments">View all →</Link></div>
          {todaysAppts.length === 0 && <p className="slate" style={{ padding: 20 }}>Nothing scheduled for today.</p>}
          {todaysAppts.map((a) => {
            const member = members[a.member_id];
            return (
              <div className="list-row" key={a.id}>
                <span className="avatar">{member ? initials(member.full_name) : '…'}</span>
                <div className="grow"><b>{member?.full_name || 'Loading…'}</b><small>{fmtTime(a.scheduled_at)} · {a.mode === 'telemedicine' ? 'Video' : 'In-person'}</small></div>
                {a.mode === 'telemedicine' && (
                  <div className="row-actions">
                    <Link className="btn primary sm" to={`/provider/call/${a.id}`}><Icon name="video" /> Join Call</Link>
                    <Link className="btn sm" to={`/provider/chat/${a.id}`}><Icon name="chat" /> Chat</Link>
                  </div>
                )}
              </div>
            );
          })}
        </section>
        <aside className="stack">
          <section className="card"><div className="card-head"><h3>Quick Actions</h3></div>
            <div className="qgrid">
              <Link to="/provider/appointments"><Icon name="clock" />Pending Approval<small>{pending ? pending.length : 0} waiting</small></Link>
              <Link to="/provider/hospital/encounter"><Icon name="hospital" />Hospital Check-in<small>Verify a member on arrival</small></Link>
              <Link to="/provider/claims"><Icon name="file" />Claims<small>Your patients' claims</small></Link>
              <Link to="/provider/support"><Icon name="phone" />Support<small>Get help</small></Link>
            </div>
          </section>
        </aside>
      </div>
    </>
  );
}
