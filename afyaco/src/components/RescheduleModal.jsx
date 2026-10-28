import { useState } from 'react';

export default function RescheduleModal({ title = 'Reschedule', onConfirm, onClose, busy }) {
  const now = new Date();
  const [date, setDate] = useState(now.toISOString().slice(0, 10));
  const [time, setTime] = useState('09:00');
  const [err, setErr] = useState('');

  function submit(e) {
    e.preventDefault();
    const iso = new Date(`${date}T${time}:00`);
    if (Number.isNaN(iso.getTime()) || iso < new Date()) {
      setErr('Pick a valid date and time in the future.');
      return;
    }
    setErr('');
    onConfirm(iso.toISOString());
  }

  return (
    <div role="dialog" aria-modal="true" aria-label={title} style={{ position: 'fixed', inset: 0, background: 'rgba(15, 30, 28, .45)', display: 'grid', placeItems: 'center', zIndex: 1000 }} onClick={() => !busy && onClose()}>
      <form className="card" style={{ maxWidth: 360, width: '100%', padding: 28 }} onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <h3 style={{ margin: '0 0 16px' }}>{title}</h3>
        <label className="field" style={{ marginTop: 0 }}>Date
          <input className="sel" type="date" required min={new Date().toISOString().slice(0, 10)} value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label className="field">Time
          <input className="sel" type="time" required value={time} onChange={(e) => setTime(e.target.value)} />
        </label>
        {err && <p className="slate" style={{ color: 'var(--warn-orange, #c0392b)', fontSize: 12 }}>{err}</p>}
        <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
          <button className="btn primary" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Confirm New Time'}</button>
          <button className="btn" type="button" disabled={busy} onClick={onClose}>Cancel</button>
        </div>
      </form>
    </div>
  );
}
