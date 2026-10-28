import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../components/Icon';
import { Banner, StatRow } from '../components/Brand';
import bannerImg from '../assets/banners/lab-tests.jpg';
import { fetchLabTests } from '../api/recommendations';
import { api, getCurrentMemberId } from '../api/client';

const POPULAR = [['Complete Blood Count (CBC)', 1200], ['Lipid Profile', 1800], ['Thyroid Function Test (TFT)', 2500], ['HbA1c (Diabetes)', 1500], ['Vitamin D', 3000]];
const HOW = [['Book Test', 'Choose a test and select a lab or collection time.'], ['Visit Lab', 'Go to the partnered lab or collect a home sample.'], ['Get Results', 'Results are uploaded securely to your profile.'], ['Take Action', 'Share with your doctor or book a follow-up consultation.']];

export default function LabTests() {
  const [tests, setTests] = useState(null);
  const [error, setError] = useState('');
  const [labs, setLabs] = useState(null);
  const [booking, setBooking] = useState(false);
  const [showBook, setShowBook] = useState(false);
  const [testName, setTestName] = useState(POPULAR[0][0]);
  const [labId, setLabId] = useState('');

  async function load() {
    try {
      const memberId = await getCurrentMemberId();
      setTests(await fetchLabTests(memberId));
    } catch (err) {
      setError(err.message || 'Could not load lab tests from the backend.');
    }
  }

  useEffect(() => {
    load();
    api.listProviders({ type: 'laboratory' }).then((ls) => { setLabs(ls); setLabId(ls[0]?.id || ''); }).catch(() => setLabs([]));
  }, []);

  async function handleBookTest(e) {
    e.preventDefault();
    if (!labId) return;
    setBooking(true);
    setError('');
    try {
      const memberId = await getCurrentMemberId();
      await api.createLabOrder({ member_id: memberId, provider_id: labId, test_name: testName });
      setShowBook(false);
      await load();
    } catch (err) {
      setError(err.message || 'Could not book this lab test.');
    } finally {
      setBooking(false);
    }
  }

  const all = tests || [];
  const completed = all.filter((t) => t.status === 'Completed').length;
  const pending = all.filter((t) => t.status === 'Pending').length;

  return (
    <>
      <Banner eyebrow="Lab tests" title={<>Accurate results.<br />Better decisions.</>} icon="flask" script={'Trusted labs,\ntrusted results.'} image={bannerImg}
        text="Book lab tests, view your results, and track your health — all in one place. Fast, secure and reliable.">
        <button className="btn primary" onClick={() => setShowBook(true)}>Book a Lab Test →</button><Link className="btn" to="/portal/lab-tests">View My Results</Link>
      </Banner>
      {showBook && (
        <section className="card" style={{ maxWidth: 480 }}>
          <div className="card-head"><h3>Book a Lab Test</h3></div>
          <form onSubmit={handleBookTest} className="stack" style={{ gap: 10 }}>
            <label className="field">Test
              <select className="sel" value={testName} onChange={(e) => setTestName(e.target.value)}>
                {POPULAR.map(([n]) => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
            <label className="field">Laboratory
              <select className="sel" value={labId} onChange={(e) => setLabId(e.target.value)} required>
                {(labs || []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn primary" type="submit" disabled={booking || !labId}>{booking ? 'Booking…' : 'Confirm Booking'}</button>
              <button className="btn" type="button" onClick={() => setShowBook(false)}>Cancel</button>
            </div>
          </form>
        </section>
      )}
      <StatRow items={[['flask', '', String(completed), 'Tests Completed', 'View your test history'], ['clock', 'violet', String(pending), 'Pending Result', "We'll notify you when it's ready"], ['cal', 'green', '0', 'Upcoming Tests', 'Scheduled for this month'], ['activity', 'blue', '0', 'Abnormal Results', 'All results are within normal range']]} />
      {error && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)' }}>{error}</p>}
      {!error && !tests && <p className="slate">Loading lab tests…</p>}
      {tests && (
      <div className="cols">
        <div className="stack">
          <section className="card">
            <div className="card-head"><h3>Recent Lab Tests</h3></div>
            <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Test name</th><th>Date</th><th>Lab / Facility</th><th>Status</th><th>Results</th></tr></thead>
              <tbody>{all.map((t) => (
                <tr key={t.id}><td><b>{t.name}</b><small>{t.sub}</small></td><td>{t.date}</td><td>{t.lab}</td>
                  <td><span className={`pill ${t.status === 'Completed' ? '' : 'orange'}`}>{t.status}</span></td>
                  <td>{t.status === 'Completed' ? <Link className="link" to={`/portal/lab-tests/${t.ref || t.id}`}>View Results →</Link> : <span className="muted">Awaiting approval</span>}</td></tr>
              ))}</tbody>
            </table>
            </div>
          </section>
          <section className="card"><div className="card-head"><h3>How it works</h3></div>
            <div className="grid g4">{HOW.map(([h, p], i) => <div key={h} style={{ display: 'flex', gap: 10 }}><span className="tile-icon">{i + 1}</span><div><b style={{ fontSize: 12.5 }}>{i + 1}. {h}</b><p className="slate" style={{ fontSize: 11 }}>{p}</p></div></div>)}</div></section>
        </div>
        <aside className="stack">
          <section className="card" style={{ textAlign: 'center' }}><h3>Book a Lab Test</h3><p className="slate" style={{ fontSize: 12, margin: '6px 0 14px' }}>Choose from a wide range of tests and get results online.</p><button className="btn primary block" onClick={() => setShowBook(true)}>Browse Tests</button></section>
          <section className="card"><div className="card-head"><h3>Popular Tests</h3></div>
            {POPULAR.map(([n, p]) => <div className="list-row" key={n} style={{ padding: '10px 0' }}><span className="tile-icon violet"><Icon name="flask" /></span><div className="grow"><b>{n}</b><small>KES {p.toLocaleString()}</small></div><Icon name="arrow" className="muted" /></div>)}</section>
        </aside>
      </div>
      )}
    </>
  );
}
