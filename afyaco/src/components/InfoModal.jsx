import Icon from './Icon';

export default function InfoModal({ icon = 'check', title, message, onClose, label = 'Got it' }) {
  return (
    <div role="dialog" aria-modal="true" aria-label={title} style={{ position: 'fixed', inset: 0, background: 'rgba(15, 30, 28, .45)', display: 'grid', placeItems: 'center', zIndex: 1000 }} onClick={onClose}>
      <div className="card" style={{ maxWidth: 380, textAlign: 'center', padding: 32 }} onClick={(e) => e.stopPropagation()}>
        <span className="tile-icon" style={{ margin: '0 auto 14px', background: 'var(--teal-pale)' }}><Icon name={icon} style={{ color: 'var(--teal-deep)' }} /></span>
        <h3 style={{ margin: '0 0 8px' }}>{title}</h3>
        {message && <p className="slate" style={{ fontSize: 13, margin: '0 0 20px' }}>{message}</p>}
        <button className="btn primary block" onClick={onClose}>{label}</button>
      </div>
    </div>
  );
}
