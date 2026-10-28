// Single source of truth for which backend roles belong to which portal —
// used by RequireAuth (redirect/gating) and main.jsx (route trees), so they
// can't silently drift apart like they just did.
export const FACILITY_ROLES = ['provider_participant', 'clinician', 'minet_ops', 'tenant_admin'];
export const MEMBER_ROLES = ['member'];
