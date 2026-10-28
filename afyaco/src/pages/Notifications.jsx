import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Icon from '../components/Icon';
import { api } from '../api/client';

function timeAgo(iso) {
  const sec = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (sec < 60) return 'just now';
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function Notifications() {
  const [list, setList] = useState(null);
  const [tab, setTab] = useState('calls');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    api.listNotifications().then(setList).catch((err) => setError(err.message || 'Could not load notifications.'));
  }, []);

  const calls = (list || []).filter((n) => n.type === 'incoming_call');
  const chats = (list || []).filter((n) => n.type === 'chat_message');
  const rows = tab === 'calls' ? calls : chats;

  async function open(n) {
    if (!n.read_at) await api.markNotificationRead(n.id).catch(() => {});
    if (n.link) navigate(n.link);
  }

  return (
    <>
      <div className="page-title"><div><h1>Notifications</h1><p>Missed calls and messages, in one place.</p></div></div>
      {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}
      <div className="tabs">
        <button className={tab === 'calls' ? 'on' : ''} onClick={() => setTab('calls')}><Icon name="video" /> Video Calls {calls.length ? `(${calls.length})` : ''}</button>
        <button className={tab === 'chats' ? 'on' : ''} onClick={() => setTab('chats')}><Icon name="chat" /> Chats {chats.length ? `(${chats.length})` : ''}</button>
      </div>
      <section className="card">
        {!list && !error && <p className="slate" style={{ padding: 20 }}>Loading…</p>}
        {list && rows.length === 0 && <p className="slate" style={{ padding: 20 }}>Nothing here yet.</p>}
        {rows.map((n) => (
          <button key={n.id} className="list-row" style={{ width: '100%', textAlign: 'left', border: 0, background: n.read_at ? 'transparent' : 'var(--teal-pale)', cursor: 'pointer' }} onClick={() => open(n)}>
            <span className={`tile-icon ${tab === 'calls' ? 'violet' : ''}`}><Icon name={tab === 'calls' ? 'video' : 'chat'} /></span>
            <div className="grow"><b>{n.title}</b><small>{n.body}</small></div>
            <small className="muted">{timeAgo(n.created_at)}</small>
          </button>
        ))}
      </section>
    </>
  );
}
