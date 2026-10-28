import { Link } from 'react-router-dom';
import Icon from '../components/Icon';
import { Brand } from '../components/Brand';

const ACTIONS = [
  ['stetho', '', 'Consult a Doctor', 'See a GP or specialist via video or in person.', 'Book now', '/portal/find-care'],
  ['pill', 'blue', 'Prescriptions', 'Get your medication filled at approved pharmacies.', 'Find dispensary', '/portal/prescriptions'],
  ['flask', 'violet', 'Laboratory Tests', 'Book tests and view results online quickly.', 'Order tests', '/portal/lab-tests'],
  ['shield', 'green', 'Check Your Cover', 'View benefits, eligibility and member details.', 'Check limits', '/portal/my-health'],
  ['file', 'blue', 'Track Claims', 'See the status of your claims in real time.', 'Live tracking', '/portal/claims'],
];
const STEPS = [
  ['Find care', 'Search for a doctor, pharmacy or lab near you.'],
  ['Book & consult', 'Choose a time, consult online or in-clinic, and get a plan.'],
  ['Get treatment', 'Receive digital prescription, pathology tests or clinical referral.'],
  ['Track & claim', 'Zero paper forms. Instant claim adjudication settled with your scheme.'],
];
const ECO = [
  ['shield', '', 'Real-Time Eligibility & Scheme Rules', 'Instant electronic scheme verification eliminates paperwork and upfront copay confusion before any clinical consultation begins.', 'Automated Rule Checks', 'var(--green)'],
  ['hospital', 'blue', 'Digital Telemedicine & E-Prescriptions', 'Encrypted video consults connected directly to national pharmacy networks for immediate digital dispatch and home delivery.', 'Direct Dispense API', 'var(--info-blue)'],
  ['flask', 'violet', 'Connected Diagnostic Labs', 'Direct digital orders with partner pathology labs. Members receive secure, clinical-grade results directly in their secure profile.', 'Encrypted Result Vault', 'var(--rx-violet)'],
  ['file', 'green', 'Automated Claims & Pre-Auth', 'AI-assisted claim adjudication that checks tariff compliance in sub-seconds with full transparency and zero duplicate submissions.', 'Real-Time Adjudication', 'var(--green)'],
];
const FAQ = [
  ['How does my medical scheme cover teleconsultations?', 'Teleconsultations booked via your insurer are integrated with your employer or scheme benefits. If your cover includes outpatient or digital health allowances, consultations are settled directly at approved contracted provider rates without any out-of-pocket cash requirements.'],
  ['How are electronic prescriptions fulfilled and delivered?', 'After your clinician issues a prescription, you choose an eligible panel pharmacy for collection or delivery. Where your scheme requires approval, Afyaco submits it to your insurer before dispensing and tracks the outcome for you.'],
  ['What happens if I need pre-authorisation for lab tests or hospitalization?', 'Afyaco checks the requirement once the service is known, assembles your clinical documents, submits the request to your insurer and keeps you updated. Emergency care is never delayed while approval is pending.'],
  ['Can I manage my family dependants under a single account?', 'Yes. Principal members can switch between themselves and registered dependants, book care on their behalf and view their claims and results subject to consent.'],
];

export default function Landing() {
  return (
    <>
      <header className="site-nav">
        <Brand />
        <nav aria-label="Main">
          <a className="on" href="#top">Home</a><a href="#find">Find Care</a><a href="#ecosystem">Ecosystem</a><a href="#how">How It Works</a><a href="#faq">Support</a>
        </nav>
        <div className="right">
          <Link className="link" to="/login">Sign in</Link>
          <Link className="btn primary sm" to="/portal">Member portal</Link>
        </div>
      </header>

      <div className="hero-wrap" id="top">
        <section className="hero">
          <div className="hero-copy">
            <span className="eyebrow">Your health. Our priority. • Connected Medical Operations</span>
            <h1>Quality healthcare,<br />made simple</h1>
            <p className="lead">Seamlessly connecting members, credentialed clinicians, pharmacies, laboratories, and real-time medical scheme coverage.</p>
            <div className="actions">
              <Link className="btn primary" to="/portal/find-care"><Icon name="cal" /> Book a consultation <Icon name="arrow" /></Link>
              <Link className="btn" to="/portal/my-health">Check your benefits</Link>
            </div>
          </div>
          <div className="hero-art">
            <span className="script">Care<br />at your<br />fingertips</span>
            <div className="figure"><Icon name="heart" /></div>
            <div className="toast-card">
              <span className="tile-icon"><Icon name="video" /></span>
              <div><b>Teleconsultation Confirmed</b><span>Your appointment is confirmed<br />Today, 10:30 AM • Dr. A. Moyo</span></div>
            </div>
          </div>
        </section>
        <div className="action-strip" id="find">
          {ACTIONS.map(([i, t, h, p, l, to]) => (
            <Link key={h} to={to}>
              <span className={`tile-icon ${t}`}><Icon name={i} /></span>
              <b>{h}</b><p>{p}</p><span className="link">{l} <Icon name="arrow" /></span>
            </Link>
          ))}
        </div>
      </div>

      <section className="section" id="how">
        <span className="eyebrow">How it works</span>
        <h2>Your complete healthcare journey, connected</h2>
        <p className="sub">Experience seamless, coordinated healthcare from verified doctor consultations to automatic medical scheme settlement.</p>
        <div className="steps">
          {STEPS.map(([h, p], i) => (
            <div className="step" key={h}>
              <span className="num">{i + 1}</span>{i < 3 && <Icon name="arrow" className="arrow" />}
              <b>{i + 1}. {h}</b><p>{p}</p>
            </div>
          ))}
        </div>
        <p style={{ marginTop: 28 }}><a className="link" href="#ecosystem">Learn more about our services <Icon name="arrow" /></a></p>
      </section>

      <section className="section" id="ecosystem">
        <span className="eyebrow">Architecture &amp; compliance</span>
        <h2>Integrated Operations Ecosystem</h2>
        <p className="sub">A seamless digital backbone connecting members, providers, and insurers with zero friction and audited governance.</p>
        <div className="eco">
          {ECO.map(([i, t, h, p, tag, c]) => (
            <div className="card" key={h}>
              <span className={`tile-icon ${t}`}><Icon name={i} /></span>
              <h3>{h}</h3><p>{p}</p>
              <span className="tag" style={{ color: c }}>{tag} <Icon name="arrow" /></span>
            </div>
          ))}
        </div>
      </section>

      <section className="section" id="faq">
        <span className="eyebrow">Questions &amp; clarifications</span>
        <h2>Frequently Asked Questions</h2>
        <p className="sub">Everything you need to know about your medical scheme cover, teleconsultations, and claims processing.</p>
        <div className="faq">
          {FAQ.map(([q, a], i) => (
            <details key={q} open={i === 0}><summary>{q}<Icon name="chevD" /></summary><p>{a}</p></details>
          ))}
        </div>
      </section>

      <footer className="footer">
        <div className="footer-in">
          <div className="sos">
            <span className="tile-icon"><Icon name="phone" /></span>
            <div><b>24/7 Clinical Emergency Assistance Line</b><span>Immediate medical evacuation, emergency admission authorizations, and crisis triage.</span></div>
            <a className="btn" href="tel:0800720000"><Icon name="phone" /> 0800 720 000 (Toll Free)</a>
          </div>
          <div className="fcols">
            <div><h4>Member Services</h4><ul><li>Find Credentialed Doctors</li><li>Prescription Deliveries</li><li>Diagnostic Lab Panels</li><li>Dependant Management</li><li>Digital Membership Card</li></ul></div>
            <div><h4>Operations &amp; Portals</h4><ul><li>Clinician Workspace</li><li>Pharmacy Dispense Portal</li><li>Pathology Lab Interface</li><li>Scheme Administrator Suite</li><li>FAWE Pre-Auth Gateway</li></ul></div>
            <div><h4>Medical Schemes</h4><ul><li>Corporate Health Benefits</li><li>SME Group Schemes</li><li>Chronic Illness Management</li><li>Wellness &amp; Health Screenings</li><li>Tariff &amp; Formulary Books</li></ul></div>
            <div><h4>Governance &amp; Trust</h4><ul><li>POPIA / Privacy Notice</li><li>Clinical Governance Board</li><li>Accessibility (WCAG 2.2 AA)</li><li>Information Security Policy</li><li>Provider Code of Conduct</li></ul></div>
            <div><Brand tagline={false} /><p style={{ marginTop: 10 }}>Afyaco Connected Medical Operations is a healthcare administration and brokerage technology platform, connecting members to care across multiple insurers.</p></div>
          </div>
          <div className="fine"><span>© 2026 Afyaco. All rights reserved. Each insurer on Afyaco remains your contracted cover provider.</span><span>Security Protocol: TLS 1.3 • ISO/IEC 27001 Certified • Terms of Operation</span></div>
        </div>
      </footer>
    </>
  );
}
