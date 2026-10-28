import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import Icon from '../components/Icon';
import { Banner, initials } from '../components/Brand';
import bannerImg from '../assets/banners/find-care.jpg';
import { api, getCurrentMemberId, session } from '../api/client';
import GoogleMapEmbed, { mapSearchUrl } from '../components/GoogleMapEmbed';
import InfoModal from '../components/InfoModal';

const EMERGENCY = /chest pain|can't breathe|cannot breathe|heavy bleeding|unconscious|suicid|seizure|stroke/i;
const CATS = [
  ['stetho', '', 'Doctors', 'General & specialist', 'doctors'],
  ['hospital', 'blue', 'Hospitals', 'Approved networks', 'hospitals'],
  ['pill', 'violet', 'Pharmacies', 'Get your medication', 'pharmacies'],
  ['flask', 'violet', 'Laboratories', 'Book diagnostic tests', 'laboratories'],
  ['video', 'green', 'Telemedicine', 'Consult online', 'telemedicine'],
];
const CAT_LABEL = { doctors: 'Top Doctors', hospitals: 'Hospitals', pharmacies: 'Pharmacies', laboratories: 'Laboratories', telemedicine: 'Telemedicine' };
const SPECS = [['stetho', 'General Medicine'], ['heart', 'Cardiology'], ['eye', 'Dermatology'], ['activity', 'Orthopedics'], ['users', 'Paediatrics'], ['shield', 'Gynaecology']];

function toUiDoc(p) {
  return {
    id: p.id,
    name: p.name,
    type: p.type,
    spec: p.specialties?.[0] || (p.type === 'pharmacy' ? 'Pharmacy' : p.type === 'laboratory' ? 'Laboratory' : p.type === 'facility' ? 'Hospital / Facility' : 'General Physician'),
    place: p.location || '—',
    tele: p.telemedicine_capable,
    net: p.network_status === 'panel' ? 'Panel' : 'Out of panel',
    latitude: p.latitude,
    longitude: p.longitude,
  };
}

export default function FindCare() {
  const [q, setQ] = useState('');
  const [spec, setSpec] = useState('All specialties');
  const [today, setToday] = useState(true);
  const [booked, setBooked] = useState(null);
  const [allProviders, setAllProviders] = useState(null);
  const [searchParams] = useSearchParams();
  const initialCategory = searchParams.get('category');
  const [category, setCategory] = useState(CAT_LABEL[initialCategory] ? initialCategory : 'doctors');
  const [error, setError] = useState('');
  const [bookingDoc, setBookingDoc] = useState(null);
  const [bookingMode, setBookingMode] = useState('physical');
  const [bookingDate, setBookingDate] = useState('');
  const [bookingTime, setBookingTime] = useState('09:00');
  const [bookingBusy, setBookingBusy] = useState(false);
  const listRef = useRef(null);

  function openBooking(d) {
    const tomorrow = new Date(Date.now() + 24 * 3600 * 1000);
    setBookingDoc(d);
    setBookingMode(d.tele ? 'telemedicine' : 'physical');
    setBookingDate(tomorrow.toISOString().slice(0, 10));
    setBookingTime('09:00');
    setError('');
  }

  async function handleBook(e) {
    e.preventDefault();
    const d = bookingDoc;
    const scheduledAt = new Date(`${bookingDate}T${bookingTime}:00`);
    if (Number.isNaN(scheduledAt.getTime()) || scheduledAt < new Date()) {
      setError('Pick a valid date and time in the future.');
      return;
    }
    setBookingBusy(true);
    setError('');
    try {
      const memberId = await getCurrentMemberId();
      await api.createAppointment({
        member_id: memberId,
        provider_id: d.id,
        mode: bookingMode,
        scheduled_at: scheduledAt.toISOString(),
        idempotency_key: `findcare-${d.id}-${Date.now()}`,
      });
      setBookingDoc(null);
      setBooked(d.name);
    } catch (err) {
      setError(err.message || 'Could not book this appointment.');
    } finally {
      setBookingBusy(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const providers = await api.listProviders();
        if (!cancelled) setAllProviders(providers.map(toUiDoc));
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load providers from the backend.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  function goToCategory(cat) {
    setCategory(cat);
    listRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  useEffect(() => {
    if (initialCategory && CAT_LABEL[initialCategory]) listRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const byCategory = {
    doctors: (d) => d.type === 'clinician',
    hospitals: (d) => d.type === 'facility',
    pharmacies: (d) => d.type === 'pharmacy',
    laboratories: (d) => d.type === 'laboratory',
    telemedicine: (d) => d.type === 'clinician' && d.tele,
  };
  const ALL = allProviders || [];
  const DOCS = ALL.filter(byCategory[category]);
  const emergency = EMERGENCY.test(q);
  const list = DOCS.filter((d) => (spec === 'All specialties' || d.spec === spec) && (!q || EMERGENCY.test(q) || `${d.name} ${d.spec} ${d.place}`.toLowerCase().includes(q.toLowerCase())));

  return (
    <>
      <Banner eyebrow="Find care" title={<>The right care,<br />when you need it.</>} icon="stetho" script={`${session.tenantName || 'Afyaco'}\nFind Care`} image={bannerImg}
        text="Find and book appointments with verified doctors, hospitals, pharmacies and labs — all within your coverage.">
        <div style={{ width: '100%' }}>
          <div className="searchbar"><Icon name="search" style={{ alignSelf: 'center', color: 'var(--muted)', marginLeft: 8 }} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search for a doctor, specialty, hospital or service..." aria-label="Search for care" /><button aria-label="Search"><Icon name="search" /></button></div>
          <div className="chips" style={{ marginTop: 12 }}>{['General Practitioner', 'Cardiologist', 'Dermatologist', 'Nearby clinics'].map((c) => <button key={c} onClick={() => setQ(c)}>{c}</button>)}</div>
        </div>
      </Banner>

      {emergency && (
        <section className="card emergency" role="alert">
          <span className="tile-icon orange"><Icon name="alert" /></span>
          <div style={{ flex: 1 }}><b>This may be an emergency.</b><p className="slate" style={{ fontSize: 12 }}>Call the 24/7 emergency line now. Cover and authorisation are handled separately and will not delay your care.</p></div>
          <a className="btn danger" href="tel:0800720000"><Icon name="phone" /> 0800 720 000</a>
        </section>
      )}
      {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}
      {bookingDoc && (
        <div role="dialog" aria-modal="true" aria-label="Book appointment" style={{ position: 'fixed', inset: 0, background: 'rgba(15, 30, 28, .45)', display: 'grid', placeItems: 'center', zIndex: 1000 }} onClick={() => !bookingBusy && setBookingDoc(null)}>
          <form className="card" style={{ maxWidth: 420, width: '100%', padding: 28 }} onClick={(e) => e.stopPropagation()} onSubmit={handleBook}>
            <h3 style={{ margin: '0 0 4px' }}>Book with {bookingDoc.name}</h3>
            <p className="slate" style={{ fontSize: 12, margin: '0 0 18px' }}>{bookingDoc.spec}</p>

            <label className="field" style={{ marginTop: 0 }}>How would you like to consult?
              <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                <button type="button" className={`btn sm${bookingMode === 'physical' ? ' primary' : ''}`} onClick={() => setBookingMode('physical')}><Icon name="hospital" /> In person</button>
                <button type="button" className={`btn sm${bookingMode === 'telemedicine' ? ' primary' : ''}`} disabled={!bookingDoc.tele} title={!bookingDoc.tele ? 'This provider does not offer telemedicine' : undefined} onClick={() => setBookingMode('telemedicine')}><Icon name="video" /> Telemedicine</button>
              </div>
            </label>

            {bookingMode === 'physical' && (
              <div className="notice info" style={{ marginTop: 12 }}>
                <Icon name="pin" />
                <div><b>{bookingDoc.place}</b> — you'll see this doctor at this location.</div>
              </div>
            )}

            <label className="field">Date
              <input className="sel" type="date" required min={new Date().toISOString().slice(0, 10)} value={bookingDate} onChange={(e) => setBookingDate(e.target.value)} />
            </label>
            <label className="field">Time
              <input className="sel" type="time" required value={bookingTime} onChange={(e) => setBookingTime(e.target.value)} />
            </label>

            {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)', fontSize: 12 }}>{error}</p>}

            <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
              <button className="btn primary" type="submit" disabled={bookingBusy}>{bookingBusy ? 'Booking…' : 'Confirm Booking'}</button>
              <button className="btn" type="button" disabled={bookingBusy} onClick={() => setBookingDoc(null)}>Cancel</button>
            </div>
          </form>
        </div>
      )}
      {booked && (
        <InfoModal
          title="Appointment reserved"
          message={<>With <b>{booked}</b>. Cover is being confirmed with {session.tenantName || 'your insurer'} — payment isn't confirmed yet and you'll be notified first.</>}
          onClose={() => setBooked(null)}
        />
      )}

      <div className="cat">
        {CATS.map(([i, t, h, p, cat]) => <button type="button" key={h} className={`card${category === cat ? ' on' : ''}`} onClick={() => goToCategory(cat)} style={{ textAlign: 'left', cursor: 'pointer' }}><span className={`tile-icon ${t}`}><Icon name={i} /></span><b>{h}</b><p>{p}</p><Icon name="arrow" className="go" /></button>)}
      </div>

      <div className="cols">
        <section ref={listRef}>
          <div className="card-head"><div><h3>{CAT_LABEL[category]}</h3><p className="slate" style={{ fontSize: 12 }}>From our verified provider panel</p></div></div>
          {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}
          {!error && !allProviders && <p className="slate" style={{ padding: 20 }}>Loading providers…</p>}
          <div className="docgrid">
            {list.map((d) => (
              <div className="card doc" key={d.id}>
                <div className="ph">{initials(d.name)}<span className={`pill ${d.net === 'Panel' ? '' : 'red'}`}>{d.net === 'Panel' ? '● Available' : 'Out of panel'}</span></div>
                <b>{d.name}</b><small>{d.spec}</small>
                {d.tele && <small><Icon name="video" style={{ color: 'var(--teal-deep)' }} /> Telemedicine available</small>}
                <small><Icon name="pin" /> {d.place}</small>
                {d.type === 'pharmacy' ? (
                  <Link className="btn sm block" to="/portal/prescriptions"><Icon name="pill" /> View Prescriptions</Link>
                ) : d.type === 'laboratory' ? (
                  <Link className="btn sm block" to="/portal/lab-tests"><Icon name="flask" /> Book a Lab Test</Link>
                ) : (
                  <button className="btn sm block" disabled={d.net !== 'Panel'} style={d.net !== 'Panel' ? { opacity: .5 } : null} onClick={() => openBooking(d)}><Icon name="cal" /> Book Appointment</button>
                )}
              </div>
            ))}
          </div>
          {allProviders && !list.length && <p className="slate" style={{ padding: 20 }}>No {CAT_LABEL[category].toLowerCase()} currently match{spec !== 'All specialties' ? ` "${spec}"` : ''}.</p>}
        </section>
        <aside className="stack">
          <section className="card">
            <div className="card-head" style={{ marginBottom: 8 }}><h3><Icon name="pin" /> Find care near you</h3><span className="muted" style={{ fontSize: 11 }} title="Location-based search isn't connected to a backend action yet">Change</span></div>
            <small className="muted">Nairobi, Kenya</small>
            <div style={{ margin: '10px 0' }}>
              <GoogleMapEmbed query={`${CAT_LABEL[category]} in Nairobi, Kenya`} title={`Map of ${CAT_LABEL[category].toLowerCase()} in Nairobi`} />
            </div>
            <a className="link" style={{ fontSize: 11.5 }} href={mapSearchUrl(`${CAT_LABEL[category]} in Nairobi, Kenya`)} target="_blank" rel="noopener noreferrer">Open in Google Maps →</a>
          </section>
          <section className="card">
            <div className="card-head"><h3>Filter results</h3><a className="link" href="#c" onClick={(e) => { e.preventDefault(); setSpec('All specialties'); setQ(''); }}>Clear all</a></div>
            <label className="field" style={{ marginTop: 0 }}>Specialty
              <select className="sel" value={spec} onChange={(e) => setSpec(e.target.value)}><option>All specialties</option>{[...new Set(DOCS.map((d) => d.spec))].map((s) => <option key={s}>{s}</option>)}</select></label>
            <label className="field">Insurance Network<select className="sel"><option>All providers</option><option>{session.tenantName || 'My insurer'} panel only</option></select></label>
            <p className="field" style={{ marginBottom: 0 }}>Availability</p>
            <label className="check"><input type="checkbox" checked={today} onChange={() => setToday(!today)} /> Today</label>
            <p className="muted" style={{ fontSize: 10.5, marginTop: 8 }}>Filters apply as you change them.</p>
          </section>
        </aside>
      </div>

      <section>
        <div className="card-head"><div><h3>Popular Specialties</h3><p className="slate" style={{ fontSize: 12 }}>Find care for your specific needs</p></div></div>
        <div className="grid g6">
          {SPECS.map(([i, s]) => <button key={s} className="card qa" style={{ textAlign: 'center', justifyItems: 'center' }} onClick={() => { setSpec(s); goToCategory('doctors'); }}><span className="tile-icon"><Icon name={i} /></span><b>{s}</b><span className="link">View doctors →</span></button>)}
        </div>
      </section>
    </>
  );
}
