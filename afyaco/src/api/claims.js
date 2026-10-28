import { api } from './client';

const STATUS_LABEL = {
  draft: 'Draft',
  submitted: 'Submitted',
  in_review: 'In Progress',
  approved: 'Approved',
  rejected: 'Rejected',
  needs_action: 'Needs Action',
  paid: 'Paid',
};

export const claimTone = (s) =>
  s === 'Approved' || s === 'Paid' ? '' : s === 'In Progress' || s === 'Submitted' ? 'orange' : s === 'Rejected' || s === 'Needs Action' ? 'red' : 'gray';

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—');
const fmtTime = (iso) => (iso ? new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : '—');

function toUiClaim(c) {
  const line = c.lines?.[0] || {};
  return {
    id: c.external_claim_id || c.id,
    svc: line.service || 'Claim',
    by: line.provider || '—',
    prov: line.provider || '—',
    loc: 'Nairobi, Kenya',
    date: fmtDate(c.submitted_at),
    time: fmtTime(c.submitted_at),
    amount: line.amount || 0,
    covered: line.covered || 0,
    member: line.member || 0,
    status: STATUS_LABEL[c.status] || c.status,
    kind: line.service || 'Claim',
  };
}

export async function fetchClaims(memberId) {
  const claims = await api.listClaims(memberId);
  return claims.map(toUiClaim);
}
