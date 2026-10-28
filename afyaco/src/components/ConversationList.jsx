import { useNavigate } from 'react-router-dom';
import { initials } from './Brand';

function timeAgo(iso) {
  const sec = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (sec < 60) return 'now';
  if (sec < 3600) return `${Math.floor(sec / 60)}m`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h`;
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Left panel for the chat screens — every consultation this user has been
// part of (brief: chat history is never lost just because one ended).
// Switching conversations re-navigates to that appointment's chat route.
export default function ConversationList({ conversations, activeAppointmentId, basePath }) {
  const navigate = useNavigate();

  return (
    <div style={{ width: 280, flexShrink: 0, background: '#fff', borderRight: '1px solid var(--border)', overflowY: 'auto' }}>
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}><b style={{ fontSize: 13 }}>Conversations</b></div>
      {conversations === null && <p className="slate" style={{ padding: 16, fontSize: 12 }}>Loading…</p>}
      {conversations && conversations.length === 0 && <p className="slate" style={{ padding: 16, fontSize: 12 }}>No conversations yet.</p>}
      {conversations && conversations.map((c) => {
        const active = c.appointment_id === activeAppointmentId;
        return (
          <button
            key={c.consultation_id}
            onClick={() => navigate(`${basePath}/${c.appointment_id}`)}
            style={{
              display: 'flex', width: '100%', gap: 10, alignItems: 'flex-start', textAlign: 'left',
              padding: '12px 16px', border: 0, borderBottom: '1px solid var(--border)', cursor: 'pointer',
              background: active ? 'var(--teal-pale)' : 'transparent',
            }}
          >
            <span className="avatar green" style={{ width: 34, height: 34, fontSize: 12, flexShrink: 0 }}>{initials(c.counterpart_name)}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6 }}>
                <b style={{ fontSize: 12.5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.counterpart_name}</b>
                <small className="muted" style={{ fontSize: 10, flexShrink: 0 }}>{timeAgo(c.last_message_at)}</small>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6, marginTop: 2 }}>
                <small className="slate" style={{ fontSize: 11, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {c.last_message || (c.mode === 'telemedicine' ? 'Video consultation' : 'In-person')}
                </small>
                {c.unread_count > 0 && <span className="badge-count">{c.unread_count}</span>}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
