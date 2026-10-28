import { NavLink, Outlet, Link } from 'react-router-dom';
import Icon from './Icon';
import { Brand } from './Brand';
import UserMenu from './UserMenu';
import NotificationBell from './NotificationBell';
import ToastStack from './ToastStack';
import useNotifications from '../hooks/useNotifications';

// Separate shell from the member PortalLayout — distinct nav, distinct top
// bar (no member identity shown here), and gated by role via RequireAuth.
const NAV = [
  ['/provider', 'Home', 'home', true],
  ['/provider/notifications', 'Notifications', 'bell', false, 'all'],
  ['/provider/appointments', 'Appointments', 'cal', false, 'chat'],
  ['/provider/claims', 'Claims', 'file'],
  ['/provider/hospital/encounter', 'Hospital Check-in', 'hospital'],
  ['/provider/support', 'Support', 'help'],
];

export default function ProviderLayout() {
  const { notifications, unreadCount, unreadChatCount, toasts, markRead, markAllRead, dismissToast } = useNotifications();

  return (
    <div className="portal">
      <header className="topbar">
        <Link to="/provider"><Brand tagline={false} /><small style={{ marginLeft: 8, color: 'var(--muted)' }}>Provider Portal</small></Link>
        <div style={{ flex: 1 }} />
        <div className="tb-right">
          <NotificationBell notifications={notifications} unreadCount={unreadCount} markRead={markRead} markAllRead={markAllRead} />
          <UserMenu fallbackIcon="hospital" />
        </div>
      </header>
      <nav className="sidebar" aria-label="Provider">
        {NAV.map(([to, label, icon, end, badgeKey]) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? 'active' : '')}>
            <Icon name={icon} />{label}
            {badgeKey === 'chat' && unreadChatCount > 0 && <span className="badge-count">{unreadChatCount}</span>}
            {badgeKey === 'all' && unreadCount > 0 && <span className="badge-count">{unreadCount}</span>}
          </NavLink>
        ))}
      </nav>
      <main className="main"><Outlet /></main>
      <ToastStack toasts={toasts} dismissToast={dismissToast} />
    </div>
  );
}
