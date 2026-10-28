import Icon from './Icon';

export function Brand({ tagline = true }) {
  return (
    <span className="brand">
      <Icon name="heart" />
      <b>Afyaco</b>
      {tagline && <small>Connected<br />Medical Operations</small>}
    </span>
  );
}

export function Stat({ icon, tone = '', label, value, note }) {
  return (
    <div className="card stat">
      <span className={`tile-icon ${tone}`}><Icon name={icon} /></span>
      <b>{value}</b><small><strong>{label}</strong></small><small className="muted">{note}</small>
    </div>
  );
}

export function PageTitle({ title, sub, children }) {
  return (
    <div className="page-title">
      <div><h1>{title}</h1>{sub && <p>{sub}</p>}</div>
      <div style={{ display: 'flex', gap: 8 }}>{children}</div>
    </div>
  );
}

export function Banner({ eyebrow, title, text, children, icon = 'heart', script = 'Care at\nyour fingertips', image }) {
  return (
    <section className={`banner${image ? ' photo' : ''}`}>
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{text}</p>
        <div className="actions">{children}</div>
      </div>
      <div className="art">
        <span className="script">{script.split('\n').map((l) => <span key={l} style={{ display: 'block' }}>{l}</span>)}</span>
        {image ? <img className="art-photo" src={image} alt="" /> : <Icon name={icon} />}
      </div>
    </section>
  );
}

export function StatRow({ items }) {
  return (
    <div className="statrow">
      {items.map(([icon, tone, value, label, note]) => (
        <div className="card" key={label}>
          <span className={`tile-icon ${tone}`}><Icon name={icon} /></span>
          <div><b>{value}</b><small>{label}</small><small>{note}</small></div>
        </div>
      ))}
    </div>
  );
}

export const initials = (n) => n.replace(/^Dr\.? /, '').split(' ').map((x) => x[0]).slice(0, 2).join('');

export function greeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}
