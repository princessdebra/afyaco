import Icon from '../components/Icon';
import { PageTitle } from '../components/Brand';

export default function Support() {
  return (
    <>
      <PageTitle title="Support" sub="We're here 24/7." />
      <div className="grid g3">
        {[['phone', 'Emergency line', '0800 720 000 (toll free)'], ['chat', 'Chat with support', 'Typical reply in under 5 minutes'], ['mail', 'Email', 'support@afyaco.example']].map(([i, t, s]) => (
          <div className="card" key={t}><span className="tile-icon"><Icon name={i} /></span><h3 style={{ margin: '10px 0 4px' }}>{t}</h3><p className="slate">{s}</p></div>
        ))}
      </div>
    </>
  );
}
