import { api } from './client';

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }) : '—');

function toUiPrescription(r) {
  const d = r.details || {};
  const dispensed = r.fulfilment?.status === 'dispensed';
  return {
    id: r.id,
    ref: d.ref,
    name: d.drug,
    form: d.dose,
    by: d.by,
    date: fmtDate(r.created_at),
    status: dispensed ? 'Completed' : 'Active',
    refills: dispensed ? `Dispensed ${fmtDate(r.fulfilment?.fulfilled_at)} · ${r.fulfilment?.provider_name || ''}` : r.fulfilment?.provider_name ? `Placed with ${r.fulfilment.provider_name}` : 'Not yet dispensed',
    auth: !r.requires_preauth ? 'Not required' : dispensed || r.fulfilment?.status === 'accepted' ? 'Approved' : 'Pre-authorisation submitted',
  };
}

export async function fetchPrescriptions(memberId) {
  const recs = await api.listRecommendations(memberId, 'prescription');
  return recs.map(toUiPrescription);
}

const LAB_STATUS = {
  result_ready: 'Completed',
  dispensed: 'Completed',
  placed: 'Pending',
  accepted: 'Pending',
  in_progress: 'Pending',
  cancelled: 'Cancelled',
};

function toUiLabTest(r) {
  const d = r.details || {};
  const status = r.requires_preauth && !r.fulfilment ? 'Pre-auth pending' : LAB_STATUS[r.fulfilment?.status] || 'Pending';
  return {
    id: r.id,
    ref: d.ref,
    name: d.test,
    sub: d.type,
    date: fmtDate(r.fulfilment?.fulfilled_at || r.created_at),
    lab: r.fulfilment?.provider_name || '—',
    status,
    resultRef: r.fulfilment?.result_ref || null,
  };
}

export async function fetchLabTests(memberId) {
  const recs = await api.listRecommendations(memberId, 'lab_test');
  return recs.map(toUiLabTest);
}
