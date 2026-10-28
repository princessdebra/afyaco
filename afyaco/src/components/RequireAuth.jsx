import { Navigate, useLocation } from 'react-router-dom';
import { session } from '../api/client';
import { FACILITY_ROLES } from '../constants/roles';

// `roles`, when given, restricts this subtree to those session roles — e.g.
// the member portal is off-limits to a `clinician` session even if logged
// in, matching the backend's own role checks on these endpoints. On a
// mismatch, send them to the portal that actually fits their role rather
// than always /portal — otherwise a denied facility role just lands in the
// member portal anyway, same bug by a different route.
export default function RequireAuth({ children, roles }) {
  const location = useLocation();
  if (!session.isAuthenticated()) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  if (roles && !roles.includes(session.role)) {
    return <Navigate to={FACILITY_ROLES.includes(session.role) ? '/provider' : '/portal'} replace />;
  }
  return children;
}
