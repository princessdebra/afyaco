import { NavLink, Outlet, Link } from 'react-router-dom';
import Icon from './Icon';
import { Brand } from './Brand';
import UserMenu from './UserMenu';
import NotificationBell from './NotificationBell';
import ToastStack from './ToastStack';
import useNotifications from '../hooks/useNotifications';

const NAV = [
  ['/portal', 'Home', 'home', true],
  ['/portal/notifications', 'Notifications', 'bell', false, 'all'],
  ['/portal/find-care', 'Find Care', 'search'],
  ['/portal/appointments', 'Appointments', 'cal'],
  ['/portal/consultations', 'Consultations', 'video', false, 'chat'],
  ['/portal/prescriptions', 'Prescriptions', 'pill'],
  ['/portal/lab-tests', 'Lab Tests', 'flask'],
  ['/portal/claims', 'Claims', 'file'],
  ['/portal/my-health', 'My Health', 'activity'],
  ['/portal/dependants', 'Dependants', 'users'],
  ['/portal/enroll', 'Identity Verification', 'shield'],
  ['/portal/support', 'Support', 'help'],
];

export default function PortalLayout() {
  const { notifications, unreadCount, unreadChatCount, toasts, markRead, markAllRead, dismissToast } = useNotifications();

  return (
    <div className="portal">
      <header className="topbar">
        <Link to="/portal"><Brand /></Link>
        <label className="search">
          <Icon name="search" />
          <input placeholder="Search doctors, hospitals, services..." aria-label="Search" />
        </label>
        <div className="tb-right">
          <NotificationBell notifications={notifications} unreadCount={unreadCount} markRead={markRead} markAllRead={markAllRead} />
          <UserMenu />
        </div>
      </header>
      <nav className="sidebar" aria-label="Portal">
        {NAV.map(([to, label, icon, end, badgeKey]) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? 'active' : '')}>
            <Icon name={icon} />{label}
            {badgeKey === 'chat' && unreadChatCount > 0 && <span className="badge-count">{unreadChatCount}</span>}
            {badgeKey === 'all' && unreadCount > 0 && <span className="badge-count">{unreadCount}</span>}
          </NavLink>
        ))}
        <div className="help">
          <b><Icon name="phone" /> Need help?</b>
          <p>Our support team is here for you 24/7</p>
          <Link className="btn sm block" to="/portal/support">Contact Support</Link>
        </div>
      </nav>
      <main className="main"><Outlet /></main>
      <ToastStack toasts={toasts} dismissToast={dismissToast} />
    </div>
  );
}
