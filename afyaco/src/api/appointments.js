import { api } from './client';

const STATUS_NOTE = {
  requested: 'Verification queued',
  confirmed: 'Cover confirmed',
  rescheduled: 'Rescheduled',
  cancelled: 'Cancelled',
  no_show: 'No-show',
  completed: 'Completed',
};

function toUiAppointment(a, providersById) {
  const provider = providersById.get(a.provider_id);
  const when = new Date(a.scheduled_at);
  const endTime = new Date(when.getTime() + 30 * 60000);
  const fmtTime = (d) => d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  return {
    id: a.id,
    m: when.toLocaleDateString('en-US', { month: 'short' }).toUpperCase(),
    d: when.getDate(),
    year: when.getFullYear(),
    t: a.mode === 'telemedicine' ? fmtTime(when) : `${fmtTime(when)} – ${fmtTime(endTime)}`,
    doc: provider?.name || 'Unknown provider',
    spec: provider?.specialties?.[0] || '',
    place: provider?.location || '—',
    type: a.mode === 'telemedicine' ? 'Virtual' : 'In-person',
    note: a.cover_confirmed ? 'Cover confirmed' : STATUS_NOTE[a.status] || a.status,
    status: a.status,
    scheduledAt: when,
  };
}

export async function fetchAppointments(memberId) {
  const [appointments, providers] = await Promise.all([api.listAppointments(memberId), api.listProviders()]);
  const providersById = new Map(providers.map((p) => [p.id, p]));
  const all = appointments.map((a) => toUiAppointment(a, providersById));
  const now = new Date();
  const upcoming = all.filter((a) => a.status !== 'completed' && a.status !== 'cancelled' && a.scheduledAt >= now).sort((a, b) => a.scheduledAt - b.scheduledAt);
  const past = all.filter((a) => a.status === 'completed' || a.scheduledAt < now).sort((a, b) => b.scheduledAt - a.scheduledAt);
  return { all, upcoming, past };
}
