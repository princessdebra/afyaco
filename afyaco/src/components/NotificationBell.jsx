import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Icon from './Icon';

function timeAgo(iso) {
  const sec = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (sec < 60) return 'just now';
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function NotificationBell({ notifications, unreadCount, markRead, markAllRead }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    function onClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  function openNotification(n) {
    if (!n.read_at) markRead(n.id);
    setOpen(false);
    if (n.link) navigate(n.link);
  }

  return (
    <div style={{ position: 'relative' }} ref={ref}>
      <button className="bell" aria-label="Notifications" onClick={() => setOpen((v) => !v)}>
        <Icon name="bell" />{unreadCount > 0 && <i />}
      </button>
      {open && (
        <div role="menu" className="card" style={{ position: 'absolute', right: 0, top: '120%', width: 'min(340px, 90vw)', maxHeight: 420, overflowY: 'auto', padding: 0, zIndex: 60 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '1px solid var(--border)' }}>
            <b style={{ fontSize: 13 }}>Notifications</b>
            {unreadCount > 0 && <button className="link" style={{ fontSize: 11.5 }} onClick={markAllRead}>Mark all read</button>}
          </div>
          {notifications.length === 0 && <p className="slate" style={{ padding: 20, fontSize: 12.5 }}>No notifications yet.</p>}
          {notifications.map((n) => (
            <button
              key={n.id}
              onClick={() => openNotification(n)}
              style={{
                display: 'block', width: '100%', textAlign: 'left', padding: '12px 14px', border: 0,
                borderBottom: '1px solid var(--border)', background: n.read_at ? 'transparent' : 'var(--teal-pale)', cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <b style={{ fontSize: 12.5 }}>{n.title}</b>
                <small className="muted" style={{ fontSize: 10, whiteSpace: 'nowrap' }}>{timeAgo(n.created_at)}</small>
              </div>
              <p className="slate" style={{ fontSize: 11.5, margin: '2px 0 0' }}>{n.body}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
