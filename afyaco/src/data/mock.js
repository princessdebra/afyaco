// Mock data. In production every record here is resolved from Minet APIs through the tenant adapter
// (member, eligibility, benefits, provider panel, pre-auth, claims). Cached values carry source + retrieval time.
export const member = {
  name: 'John Mwangi', initials: 'JM', ref: 'MNT-0942-SC8591', scheme: 'Minet Comprehensive Executive',
  policy: 'POL-MIN-884270', role: 'Principal', retrieved: 'Today, 09:12 · Minet Eligibility API',
};

export const benefits = [
  { name: 'Inpatient Cover', used: 'KES 98,000', limit: 'KES 1,820,000', pct: 5, left: '95% remaining', tone: '' },
  { name: 'Outpatient Cover', used: 'KES 120,000', limit: 'KES 198,000', pct: 61, left: '39.1% remaining', tone: 'blue' },
  { name: 'Optical & Dental', used: 'KES 11,500', limit: 'KES 35,000', pct: 33, left: '67% remaining', tone: 'orange' },
];

export const appointments = [
  { id: 'A1', doctor: 'Dr. Amina Njoroge', spec: 'General Physician', mode: 'Teleconsultation', when: '12 Oct 2026 · 10:30 AM', place: 'Video consultation', status: 'Confirmed', cover: 'Covered · KES 0 co-pay' },
  { id: 'A2', doctor: 'Dr. Peter Otieno', spec: 'Cardiologist', mode: 'Physical visit', when: '18 Oct 2026 · 02:00 PM', place: 'Aga Khan Hospital, Parklands', status: 'Awaiting pre-auth', cover: 'Pre-authorisation required' },
  { id: 'A3', doctor: 'Dr. Lydia Kamau', spec: 'Dermatologist', mode: 'Teleconsultation', when: '24 Oct 2026 · 09:00 AM', place: 'Video consultation', status: 'Verification queued', cover: 'Eligibility being verified' },
];

export const providers = [
  { name: 'Dr. Amina Njoroge', spec: 'General Physician', loc: 'Teleconsultation', net: 'Panel', rating: 4.9, next: 'Today 10:30', tele: true },
  { name: 'Dr. Peter Otieno', spec: 'Cardiologist', loc: 'Parklands, Nairobi', net: 'Panel', rating: 4.8, next: 'Tue 14:00', tele: false },
  { name: 'Dr. Lydia Kamau', spec: 'Dermatologist', loc: 'Teleconsultation', net: 'Panel', rating: 4.7, next: 'Thu 09:00', tele: true },
  { name: 'Dr. Samuel Kiprop', spec: 'Paediatrician', loc: 'Westlands, Nairobi', net: 'Panel', rating: 4.9, next: 'Mon 11:15', tele: true },
  { name: 'Dr. Halima Yusuf', spec: 'Gynaecologist', loc: 'Karen, Nairobi', net: 'Out of panel', rating: 4.6, next: 'Fri 15:30', tele: false },
];

export const facilities = [
  { name: 'Aga Khan University Hospital', kind: 'Hospital', loc: 'Parklands', net: 'Panel' },
  { name: 'Nairobi Hospital', kind: 'Hospital', loc: 'Upper Hill', net: 'Panel' },
  { name: 'Lancet Kenya Laboratories', kind: 'Laboratory', loc: 'Multiple branches', net: 'Panel' },
  { name: 'Goodlife Pharmacy', kind: 'Pharmacy', loc: 'Delivery & collection', net: 'Panel' },
];

export const prescriptions = [
  { id: 'RX-20841', drug: 'Amoxicillin 500mg', dose: '1 capsule · 3× daily · 7 days', by: 'Dr. Amina Njoroge', status: 'Active', pharm: 'Goodlife Pharmacy', auth: 'Not required', date: '12 Oct 2026' },
  { id: 'RX-20790', drug: 'Metformin 850mg', dose: '1 tablet · 2× daily · 30 days', by: 'Dr. Peter Otieno', status: 'Pre-auth pending', pharm: '—', auth: 'Submitted to Minet', date: '08 Oct 2026' },
  { id: 'RX-20512', drug: 'Cetirizine 10mg', dose: '1 tablet · nightly · 14 days', by: 'Dr. Lydia Kamau', status: 'Dispensed', pharm: 'Haltons Pharmacy', auth: 'Not required', date: '29 Sep 2026' },
  { id: 'RX-20377', drug: 'Atorvastatin 20mg', dose: '1 tablet · nightly · 30 days', by: 'Dr. Peter Otieno', status: 'Dispensed', pharm: 'Goodlife Pharmacy', auth: 'Approved', date: '15 Sep 2026' },
];

export const labTests = [
  { id: 'LAB-5521', test: 'Complete Blood Count', lab: 'Lancet Kenya', status: 'Result available', date: '10 Oct 2026', auth: 'Not required' },
  { id: 'LAB-5530', test: 'Lipid Profile', lab: 'Pathcare', status: 'Pending result', date: '11 Oct 2026', auth: 'Approved' },
  { id: 'LAB-5544', test: 'MRI Lumbar Spine', lab: 'Nairobi Hospital', status: 'Pre-auth pending', date: '—', auth: 'Information requested' },
  { id: 'LAB-5470', test: 'HbA1c', lab: 'Lancet Kenya', status: 'Result available', date: '22 Sep 2026', auth: 'Not required' },
];

export const claims = [
  { id: 'CLM-78493', provider: 'Aga Khan Hospital', service: 'Consultation & labs', date: '10 Oct 2026', claimed: 14500, covered: 14500, member: 0, status: 'Accepted' },
  { id: 'CLM-78211', provider: 'Goodlife Pharmacy', service: 'Pharmacy', date: '04 Oct 2026', claimed: 3200, covered: 2880, member: 320, status: 'In review' },
  { id: 'CLM-77980', provider: 'Lancet Kenya', service: 'Diagnostics', date: '29 Sep 2026', claimed: 9800, covered: 9800, member: 0, status: 'Paid' },
  { id: 'CLM-77412', provider: 'Nairobi Hospital', service: 'Specialist consultation', date: '18 Sep 2026', claimed: 8500, covered: 0, member: 8500, status: 'Additional information needed' },
];

export const dependants = [
  { name: 'Grace Mwangi', rel: 'Spouse', age: 34, status: 'Active', cover: 'Minet Comprehensive Executive' },
  { name: 'Brian Mwangi', rel: 'Child', age: 9, status: 'Active', cover: 'Minet Comprehensive Executive' },
  { name: 'Faith Mwangi', rel: 'Child', age: 4, status: 'Active', cover: 'Minet Comprehensive Executive' },
];

export const activity = [
  ['flask', 'Lab test result available', 'Complete blood count · 3 hours ago', 'violet'],
  ['pill', 'Prescription issued', 'Amoxicillin 500mg · 3 hours ago', 'blue'],
  ['cal', 'Appointment completed', 'Dr. Amina Njoroge · Yesterday', ''],
  ['file', 'Claim accepted', 'CLM-78493 · 2 days ago', 'green'],
];

export const money = (n) => `KES ${n.toLocaleString()}`;
export const statusTone = (s) =>
  /accepted|paid|dispensed|confirmed|active|available|approved|panel/i.test(s) ? '' :
  /pending|queued|awaiting|review|required|submitted/i.test(s) ? 'orange' :
  /information|needed|out of/i.test(s) ? 'red' : 'gray';
