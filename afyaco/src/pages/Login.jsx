import { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import Icon from '../components/Icon';
import { Brand } from '../components/Brand';
import { api, session } from '../api/client';
import { FACILITY_ROLES } from '../constants/roles';

export default function Login() {
  const nav = useNavigate();
  const location = useLocation();
  const [show, setShow] = useState(false);
  const [id, setId] = useState('');
  const [pw, setPw] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      // The tenant/insurer is resolved server-side from the account itself
      // (email is globally unique) — never chosen by the person signing in.
      const { access_token, role, full_name, tenant_slug, tenant_name } = await api.login(id, pw);
      session.set({ token: access_token, tenantSlug: tenant_slug, tenantName: tenant_name, role, fullName: full_name });
      // RequireAuth remembers where an unauthenticated visit was headed (e.g.
      // a scanned QR's /portal/verify-visit?token=...) — send them back there.
      // Otherwise, land staff roles in the provider portal and members in
      // their own portal, rather than always defaulting to the member view.
      const from = location.state?.from;
      const target = from
        ? `${from.pathname}${from.search || ''}`
        : FACILITY_ROLES.includes(role) ? '/provider' : '/portal';
      nav(target, { replace: true });
    } catch (err) {
      setError(err.message || 'Sign in failed');
    } finally {
      setBusy(false);
    }
  }; // TODO: replace with each tenant's own identity provider (OIDC + MFA)

  return (
    <div className="login-page">
      <div className="login-card">
        <section className="login-art">
          <Brand />
          <span className="pill" style={{ alignSelf: 'flex-start' }}><Icon name="shield" /> Pan-African Digital Care Network</span>
          <h1>Better care,<span>together.</span></h1>
          <p className="slate" style={{ fontSize: 13 }}>One platform. Your health. Our priority.<br />Access healthcare, manage your benefits, and stay connected all in one place.</p>
          <div className="mini">
            {[['stetho', 'Consult Doctors'], ['pill', 'Get Prescriptions'], ['flask', 'Book Lab Tests'], ['hospital', 'Find Hospitals'], ['shield', 'Track Claims']].map(([i, l]) => (
              <div key={l}><Icon name={i} />{l}</div>
            ))}
          </div>
          <p className="script">Health<br />connects<br />us all</p>
        </section>
        <form className="login-form" onSubmit={submit}>
          <div className="top">Need help?&nbsp;<Icon name="phone" /></div>
          <h2>Welcome back</h2>
          <p className="slate" style={{ fontSize: 12.5 }}>Sign in to your account to continue</p>
          <label className="field">Email or Phone Number
            <span className="input"><Icon name="mail" /><input value={id} onChange={(e) => setId(e.target.value)} placeholder="Enter your email or phone number" autoComplete="username" /></span>
          </label>
          <label className="field">Password
            <span className="input"><Icon name="lock" />
              <input type={show ? 'text' : 'password'} value={pw} onChange={(e) => setPw(e.target.value)} placeholder="Enter your password" autoComplete="current-password" />
              <button type="button" onClick={() => setShow(!show)} aria-label="Toggle password" style={{ border: 0, background: 'none', color: 'inherit' }}><Icon name="eye" /></button>
            </span>
          </label>
          <div className="row">
            <label><input type="checkbox" defaultChecked /> Remember me</label>
            <a className="link" href="#reset">Forgot password?</a>
          </div>
          {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)', fontSize: 12 }}>{error}</p>}
          <button className="btn primary block" type="submit" disabled={busy}>{busy ? 'Signing in…' : <>Sign in <Icon name="arrow" /></>}</button>
          <div className="divider">or</div>
          <button className="btn block" type="button" style={{ borderColor: 'var(--border)', color: 'var(--navy)' }}>Continue with Google</button>
          <p className="slate" style={{ textAlign: 'center', fontSize: 11.5, marginTop: 14 }}>Don't have an account? <Link className="link" to="/login">Create one</Link></p>
          <div className="trust"><span><Icon name="shield" /> Your data is secure and protected</span><span><Icon name="lock" /> Powered by Xenova</span></div>
        </form>
      </div>
    </div>
  );
}
