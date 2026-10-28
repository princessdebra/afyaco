import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Icon from './Icon';
import { initials } from './Brand';
import { session } from '../api/client';

const ROLE_LABEL = {
  member: 'Member',
  provider_participant: 'Provider staff',
  minet_ops: 'MIP operations',
  tenant_admin: 'Tenant admin',
  clinician: 'Clinician',
  pharmacy: 'Pharmacy',
  laboratory: 'Laboratory',
  claims_officer: 'Claims officer',
};

export default function UserMenu({ fallbackIcon }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();
  const name = session.fullName || ROLE_LABEL[session.role] || 'Account';
  const roleLabel = ROLE_LABEL[session.role] || session.role;

  useEffect(() => {
    function onClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  function signOut() {
    session.clear();
    navigate('/login', { replace: true });
  }

  return (
    <div style={{ position: 'relative' }} ref={ref}>
      <button className="user" onClick={() => setOpen((v) => !v)} aria-haspopup="menu" aria-expanded={open}>
        <span className="avatar">{fallbackIcon ? <Icon name={fallbackIcon} /> : initials(name)}</span>
        <div><b>{name}</b><small>{roleLabel}</small></div>
        <Icon name="chevD" className="muted" />
      </button>
      {open && (
        <div role="menu" className="card" style={{ position: 'absolute', right: 0, top: '110%', width: 200, padding: 6, zIndex: 50 }}>
          <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--border)', marginBottom: 4 }}>
            <b style={{ fontSize: 12.5, display: 'block' }}>{name}</b>
            <small className="muted">{roleLabel}</small>
          </div>
          <button role="menuitem" className="menu-item" onClick={signOut}>
            <Icon name="x" /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}
