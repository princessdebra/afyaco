// Thin client for the Afyaco backend (backend/app — FastAPI).
// Defaults to '' (same-origin, relative paths) so requests go through Vite's
// dev proxy (see vite.config.js: '/api' -> localhost:8200) — this works
// whether the page is opened as localhost:5173 or through an ngrok/tunnel
// hostname on a phone, with no CORS involved either way. Set
// VITE_API_BASE_URL only to point at a backend NOT reachable from the
// machine running `vite` itself (e.g. a fully separate deployed API).
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

const TOKEN_KEY = 'afyaco.token';
const TENANT_KEY = 'afyaco.tenant';
const TENANT_NAME_KEY = 'afyaco.tenantName';
const ROLE_KEY = 'afyaco.role';
const NAME_KEY = 'afyaco.name';

export const session = {
  get token() {
    return localStorage.getItem(TOKEN_KEY);
  },
  get tenantSlug() {
    return localStorage.getItem(TENANT_KEY);
  },
  // The insurer/organisation's display name, as the backend named it at
  // login — never hardcode an insurer name in a page, use this instead.
  get tenantName() {
    return localStorage.getItem(TENANT_NAME_KEY);
  },
  get role() {
    return localStorage.getItem(ROLE_KEY);
  },
  get fullName() {
    return localStorage.getItem(NAME_KEY);
  },
  isAuthenticated() {
    return Boolean(localStorage.getItem(TOKEN_KEY));
  },
  set({ token, tenantSlug, tenantName, role, fullName }) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(TENANT_KEY, tenantSlug);
    if (tenantName) localStorage.setItem(TENANT_NAME_KEY, tenantName);
    localStorage.setItem(ROLE_KEY, role);
    if (fullName) localStorage.setItem(NAME_KEY, fullName);
    resetMemberCache();
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TENANT_KEY);
    localStorage.removeItem(TENANT_NAME_KEY);
    localStorage.removeItem(ROLE_KEY);
    localStorage.removeItem(NAME_KEY);
    resetMemberCache();
  },
};

class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth && session.token) headers.Authorization = `Bearer ${session.token}`;

  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    throw new ApiError(
      `Could not reach the backend at ${BASE_URL}. Is the SSH tunnel to the devserver open?`,
      0,
      null
    );
  }

  if (res.status === 401) {
    session.clear();
  }

  if (!res.ok) {
    const payload = await res.json().catch(() => null);
    const message = payload?.detail ? JSON.stringify(payload.detail) : `Request failed (${res.status})`;
    throw new ApiError(message, res.status, payload);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  login: (email, password) =>
    request('/api/v1/auth/login', {
      method: 'POST',
      auth: false,
      body: { email, password },
    }),

  getMyMember: () => request('/api/v1/members/me'),
  getMember: (externalRef) => request(`/api/v1/members/${externalRef}`),
  getMemberById: (id) => request(`/api/v1/members/by-id/${id}`),
  getMemberBenefits: (externalRef) => request(`/api/v1/members/${externalRef}/benefits`),
  getDependants: (externalRef) => request(`/api/v1/members/${externalRef}/dependants`),

  listProviders: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/api/v1/providers${qs ? `?${qs}` : ''}`);
  },

  listRecommendations: (memberId, kind) =>
    request(`/api/v1/recommendations?member_id=${memberId}${kind ? `&kind=${kind}` : ''}`),

  listAppointments: (memberId) =>
    request(`/api/v1/appointments${memberId ? `?member_id=${memberId}` : ''}`),
  getAppointment: (id) => request(`/api/v1/appointments/${id}`),
  createAppointment: (payload) => request('/api/v1/appointments', { method: 'POST', body: payload }),
  cancelAppointment: (id) => request(`/api/v1/appointments/${id}/cancel`, { method: 'POST' }),
  rescheduleAppointment: (id, scheduledAt) =>
    request(`/api/v1/appointments/${id}/reschedule`, { method: 'POST', body: { scheduled_at: scheduledAt } }),

  startConsultation: (appointmentId) =>
    request('/api/v1/consultations/start', { method: 'POST', body: { appointment_id: appointmentId } }),
  endConsultation: (id) => request(`/api/v1/consultations/${id}/end`, { method: 'POST' }),

  listClaims: (memberId) => request(`/api/v1/claims${memberId ? `?member_id=${memberId}` : ''}`),
  getClaim: (id) => request(`/api/v1/claims/${id}`),
  createClaim: (payload) => request('/api/v1/claims', { method: 'POST', body: payload }),

  createPreauth: (payload) => request('/api/v1/preauth', { method: 'POST', body: payload }),
  getPreauth: (id) => request(`/api/v1/preauth/${id}`),

  createLabOrder: (payload) => request('/api/v1/recommendations/lab-order', { method: 'POST', body: payload }),
  refillPrescription: (recommendationId) =>
    request(`/api/v1/recommendations/${recommendationId}/refill`, { method: 'POST' }),

  listPendingAppointments: () => request('/api/v1/appointments/pending'),
  listMyProviderAppointments: () => request('/api/v1/appointments/mine'),
  listMyPatientsClaims: () => request('/api/v1/claims/mine'),
  confirmAppointment: (id) => request(`/api/v1/appointments/${id}/confirm`, { method: 'POST' }),
  declineAppointment: (id) => request(`/api/v1/appointments/${id}/decline`, { method: 'POST' }),

  getChatMessages: (consultationId) => request(`/api/v1/chat/${consultationId}/messages`),

  listMyConversations: () => request('/api/v1/consultations/mine'),
  getConsultationByAppointment: (appointmentId) => request(`/api/v1/consultations/by-appointment/${appointmentId}`),

  listNotifications: () => request('/api/v1/notifications'),
  getUnreadCount: () => request('/api/v1/notifications/unread-count'),
  markNotificationRead: (id) => request(`/api/v1/notifications/${id}/read`, { method: 'POST' }),
  markAllNotificationsRead: () => request('/api/v1/notifications/read-all', { method: 'POST' }),
};

function wsBaseUrl() {
  const base = BASE_URL || window.location.origin;
  return base.replace(/^http/, 'ws');
}

// WebSocket URL for a chat room — converts the same BASE_URL/relative-proxy
// logic the REST client uses into a ws(s):// URL, since fetch() and
// WebSocket don't share a base.
export function chatWsUrl(consultationId) {
  return `${wsBaseUrl()}/api/v1/chat/${consultationId}/ws?token=${encodeURIComponent(session.token || '')}`;
}

// One socket per session — every message/appointment-reminder notification
// for the logged-in user arrives here, regardless of which page they're on.
export function notificationsWsUrl() {
  return `${wsBaseUrl()}/api/v1/notifications/ws?token=${encodeURIComponent(session.token || '')}`;
}

// WebRTC signaling relay for a given consultation's video call — carries SDP/
// ICE messages only, never media (that's peer-to-peer once connected).
export function callSignalWsUrl(consultationId) {
  return `${wsBaseUrl()}/api/v1/call/${consultationId}/signal?token=${encodeURIComponent(session.token || '')}`;
}

// Cached lookup of the logged-in user's own member record — resolved via
// /members/me (backed by User.member_id), not a hardcoded demo member, so
// this works for whichever tenant/member is actually signed in.
let memberPromise = null;
export function getCurrentMember() {
  if (!memberPromise) {
    memberPromise = api.getMyMember();
  }
  return memberPromise;
}
export function getCurrentMemberId() {
  return getCurrentMember().then((m) => m.id);
}
export function resetMemberCache() {
  memberPromise = null;
}

export { ApiError, BASE_URL };
