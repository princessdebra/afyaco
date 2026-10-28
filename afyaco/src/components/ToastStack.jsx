import { useNavigate } from 'react-router-dom';
import Icon from './Icon';

export default function ToastStack({ toasts, dismissToast }) {
  const navigate = useNavigate();
  if (!toasts.length) return null;

  return (
    <div style={{ position: 'fixed', top: 16, right: 16, left: 16, zIndex: 2000, display: 'grid', gap: 10, width: 'min(320px, 100%)', marginLeft: 'auto' }}>
      {toasts.map((t) => (
        <div
          key={t.id}
          className="card"
          style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: 14, cursor: t.link ? 'pointer' : 'default', boxShadow: '0 10px 30px rgba(15,30,28,.2)' }}
          onClick={() => { dismissToast(t.id); if (t.link) navigate(t.link); }}
        >
          <span className="tile-icon violet"><Icon name={t.type === 'chat_message' ? 'chat' : 'bell'} /></span>
          <div style={{ flex: 1 }}>
            <b style={{ fontSize: 12.5, display: 'block' }}>{t.title}</b>
            <small className="slate" style={{ fontSize: 11.5 }}>{t.body}</small>
          </div>
          <button
            aria-label="Dismiss"
            onClick={(e) => { e.stopPropagation(); dismissToast(t.id); }}
            style={{ border: 0, background: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 14, lineHeight: 1 }}
          >
            <Icon name="x" style={{ width: 14, height: 14 }} />
          </button>
        </div>
      ))}
    </div>
  );
}
