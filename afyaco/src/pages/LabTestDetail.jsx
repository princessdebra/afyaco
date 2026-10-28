import { Link, useParams } from 'react-router-dom';
import Icon from '../components/Icon';

const RES = [['Total Cholesterol', '4.8', 'mmol/L', '< 5.2'], ['HDL Cholesterol', '1.4', 'mmol/L', '> 1.0'], ['LDL Cholesterol', '2.6', 'mmol/L', '< 3.4'], ['Triglycerides', '1.2', 'mmol/L', '< 1.7'], ['Total/HDL Ratio', '3.4', 'Ratio', '< 5.0']];
const STAT = [['Test Ordered', 'Sep 27, 2026 • 11:40 AM', 'Order created by Dr. Amina Njoroge'], ['Sample Collected', 'Sep 28, 2026 • 08:15 AM', 'Sample taken at Nairobi Health Labs'], ['Result Processed', 'Sep 28, 2026 • 01:30 PM', 'Results ready and verified'], ['Results Available', 'Sep 28, 2026 • 02:30 PM', 'You can now view and download your results']];

export default function LabTestDetail() {
  const { id } = useParams();
  return (
    <>
      <Link to="/portal/lab-tests" className="back"><Icon name="arrow" style={{ transform: 'rotate(180deg)' }} /> Back to Lab Tests</Link>
      <div className="page-title"><div><h1>Lab Test Details <span className="pill">✓ Completed</span></h1><p>View your lab test information, results and next steps.</p></div><small className="muted">#{id}</small></div>
      <div className="cols">
        <div className="stack">
          <div className="notice ok" style={{ alignItems: 'center' }}><Icon name="check" /><div style={{ flex: 1 }}><b>Test Results Available</b><br />Your test results are ready. View and download your report.</div><button className="btn primary sm"><Icon name="file" /> Download Report</button></div>
          <section className="card"><h3 style={{ marginBottom: 14 }}>Test Information</h3>
            <div className="kv">{[['flask', 'Test Name', 'Lipid Profile'], ['hospital', 'Lab', 'Nairobi Health Labs'], ['file', 'Test ID', id], ['activity', 'Test Type', 'Blood Test'], ['cal', 'Sample Collection Date', 'Sep 28, 2026 08:15 AM'], ['file', 'Order Number', 'ORD-77654'], ['stetho', 'Ordered By', 'Dr. Amina Njoroge'], ['cal', 'Result Date', 'Sep 28, 2026 02:30 PM']].map(([i, l, v]) => <div key={l}><Icon name={i} /><span><small>{l}</small><b>{v}</b></span></div>)}</div></section>
          <section className="card"><h3 style={{ marginBottom: 8 }}>Test Results</h3>
            <div className="table-wrap"><table className="table"><thead><tr><th>Parameter</th><th>Result</th><th>Unit</th><th>Reference range</th><th>Status</th></tr></thead>
              <tbody>{RES.map(([p, r, u, ref]) => <tr key={p}><td><b>{p}</b></td><td><b>{r}</b></td><td>{u}</td><td>{ref}</td><td><span className="pill">Normal</span></td></tr>)}</tbody></table></div>
            <div className="notice ok" style={{ marginTop: 14, alignItems: 'center' }}><Icon name="check" /><div style={{ flex: 1 }}><b>Overall Result: Normal</b><br />Your lipid profile is within the normal range. Keep up the good work!</div><button className="btn sm">View Interpretation →</button></div></section>
          <div className="notice info" style={{ alignItems: 'center' }}><Icon name="chat" /><div style={{ flex: 1 }}><b>Need to do more?</b> Book a follow-up consultation to discuss your results with your doctor.</div><Link className="btn sm" to="/portal/find-care">Book Appointment →</Link></div>
        </div>
        <aside className="stack">
          <section className="card"><h3 style={{ marginBottom: 12 }}>Test Status</h3><ul className="timeline">{STAT.map(([t, d, s]) => <li key={t}><i className="done" /><div><b>{t}</b><small>{d}</small><small>{s}</small></div></li>)}</ul></section>
          <section className="card"><h3 style={{ marginBottom: 12 }}>Quick Actions</h3>
            <div className="qgrid"><button><Icon name="file" />Download Report<small>Get your full report (PDF)</small></button><button><Icon name="activity" />View Interpretation<small>Understand your results</small></button><Link to="/portal/find-care"><Icon name="cal" />Book Follow-up<small>Schedule a consultation</small></Link><Link to="/portal/support"><Icon name="phone" />Contact Support<small>Get help</small></Link></div></section>
          <section className="card"><b>Need Help?</b><p className="slate" style={{ fontSize: 12, margin: '4px 0 10px' }}>Our support team is here to help you with your lab tests.</p><Link className="btn sm block" to="/portal/support">Contact Support</Link></section>
        </aside>
      </div>
    </>
  );
}
