import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Icon from '../../components/Icon';
import { initials } from '../../components/Brand';
import { api } from '../../api/client';

function fmtDateTime(iso) {
  const d = new Date(iso);
  return `${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} · ${d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`;
}

export default function ProviderAppointments() {
  const [tab, setTab] = useState('pending');
  const [pending, setPending] = useState(null);
  const [confirmed, setConfirmed] = useState(null);
  const [members, setMembers] = useState({});
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const navigate = useNavigate();

  async function loadMembers(appts) {
    const ids = [...new Set(appts.map((a) => a.member_id))].filter((id) => !members[id]);
    if (!ids.length) return;
    const fetched = await Promise.all(ids.map((id) => api.getMemberById(id).catch(() => null)));
    setMembers((m) => {
      const next = { ...m };
      ids.forEach((id, i) => { if (fetched[i]) next[id] = fetched[i]; });
      return next;
    });
  }

  async function load() {
    try {
      const [p, c] = await Promise.all([api.listPendingAppointments(), api.listMyProviderAppointments()]);
      setPending(p);
      setConfirmed(c);
      await loadMembers([...p, ...c]);
    } catch (err) {
      setError(err.message || 'Could not load appointments.');
    }
  }

  useEffect(() => { load(); }, []);

  async function handleConfirm(id) {
    setBusyId(id);
    setError('');
    try {
      await api.confirmAppointment(id);
      await load();
    } catch (err) {
      setError(err.message || 'Could not confirm this appointment.');
    } finally {
      setBusyId(null);
    }
  }

  async function handleDecline(id) {
    if (!window.confirm('Decline this appointment request? The member will need to rebook.')) return;
    setBusyId(id);
    setError('');
    try {
      await api.declineAppointment(id);
      await load();
    } catch (err) {
      setError(err.message || 'Could not decline this appointment.');
    } finally {
      setBusyId(null);
    }
  }

  const list = tab === 'pending' ? pending : confirmed;

  return (
    <>
      <div className="page-title"><div><h1>Appointments</h1><p>Approve incoming requests and open consultations with your patients.</p></div></div>
      {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}
      <div className="tabs">
        <button className={tab === 'pending' ? 'on' : ''} onClick={() => setTab('pending')}>Pending {pending ? `(${pending.length})` : ''}</button>
        <button className={tab === 'confirmed' ? 'on' : ''} onClick={() => setTab('confirmed')}>Confirmed {confirmed ? `(${confirmed.length})` : ''}</button>
      </div>
      <section className="card">
        {!list && <p className="slate" style={{ padding: 20 }}>Loading…</p>}
        {list && list.length === 0 && <p className="slate" style={{ padding: 20 }}>{tab === 'pending' ? 'No appointments waiting on your approval.' : 'No confirmed appointments yet.'}</p>}
        {list && list.map((a) => {
          const member = members[a.member_id];
          return (
            <div className="list-row" key={a.id}>
              <span className="avatar">{member ? initials(member.full_name) : '…'}</span>
              <div className="grow">
                <b>{member?.full_name || 'Loading…'}</b>
                <small>{a.mode === 'telemedicine' ? 'Video consultation' : 'In-person'} · {fmtDateTime(a.scheduled_at)}</small>
                {a.reason && <small className="muted">{a.reason}</small>}
              </div>
              <span className={`pill ${a.mode === 'telemedicine' ? 'violet' : 'blue'}`}>{a.mode === 'telemedicine' ? 'Virtual' : 'In-person'}</span>
              <div className="row-actions">
                {tab === 'pending' ? (
                  <>
                    <button className="btn primary sm" disabled={busyId === a.id} onClick={() => handleConfirm(a.id)}>{busyId === a.id ? 'Confirming…' : 'Confirm'}</button>
                    <button className="btn sm" disabled={busyId === a.id} onClick={() => handleDecline(a.id)}>Decline</button>
                  </>
                ) : (
                  a.mode === 'telemedicine' && a.status !== 'completed' && (
                    <>
                      <button className="btn primary sm" onClick={() => navigate(`/provider/call/${a.id}`)}><Icon name="video" /> Join Call</button>
                      <button className="btn sm" onClick={() => navigate(`/provider/chat/${a.id}`)}><Icon name="chat" /> Chat</button>
                    </>
                  )
                )}
              </div>
            </div>
          );
        })}
      </section>
    </>
  );
}
