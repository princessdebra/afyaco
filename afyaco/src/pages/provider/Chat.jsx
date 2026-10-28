import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Icon from '../../components/Icon';
import { initials } from '../../components/Brand';
import ConversationList from '../../components/ConversationList';
import { api } from '../../api/client';
import useChatRoom from '../../hooks/useChatRoom';

function fmtTime(d) {
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

export default function ProviderChat() {
  const { appointmentId } = useParams();
  const navigate = useNavigate();
  const [member, setMember] = useState(null);
  const [consultation, setConsultation] = useState(null);
  const [conversations, setConversations] = useState(null);
  const [setupError, setSetupError] = useState('');
  const [draft, setDraft] = useState('');
  const [ending, setEnding] = useState(false);
  const listEndRef = useRef(null);
  const textareaRef = useRef(null);

  const { messages, connected, counterpartTyping, error, send, sendTyping, markRead } = useChatRoom(consultation?.id, 'clinician');

  useEffect(() => {
    api.listMyConversations().then(setConversations).catch(() => setConversations([]));
  }, [appointmentId]);

  useEffect(() => {
    let cancelled = false;
    setConsultation(null);
    setSetupError('');
    (async () => {
      try {
        const appt = await api.getAppointment(appointmentId);
        if (cancelled) return;
        const m = await api.getMemberById(appt.member_id).catch(() => null);
        if (cancelled) return;
        setMember(m);
        let c;
        try {
          c = await api.startConsultation(appointmentId);
        } catch {
          c = await api.getConsultationByAppointment(appointmentId);
        }
        if (cancelled) return;
        setConsultation(c);
      } catch (err) {
        if (!cancelled) setSetupError(err.message || 'Could not open this consultation.');
      }
    })();
    return () => { cancelled = true; };
  }, [appointmentId]);

  useEffect(() => { listEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, counterpartTyping]);

  useEffect(() => {
    if (messages.some((m) => m.from === 'member')) markRead();
    if (messages.length) api.listMyConversations().then(setConversations).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length]);

  function autoResize() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }

  function handleSend() {
    send(draft);
    setDraft('');
    requestAnimationFrame(autoResize);
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    } else {
      sendTyping();
    }
  }

  async function handleEnd() {
    setEnding(true);
    try {
      if (consultation) await api.endConsultation(consultation.id);
    } catch {
      // ignore
    } finally {
      navigate('/provider/appointments');
    }
  }

  const groups = [];
  for (const m of messages) {
    const last = groups[groups.length - 1];
    if (last && last.from === m.from) last.items.push(m);
    else groups.push({ from: m.from, items: [m] });
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'var(--bg, #f4f8f7)', zIndex: 1000, display: 'flex' }}>
    <ConversationList conversations={conversations} activeAppointmentId={appointmentId} basePath="/provider/chat" />
    <div style={{ flex: 1, minWidth: 0, display: 'grid', gridTemplateRows: 'auto 1fr auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 20px', background: '#fff', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button className="btn sm" style={{ borderRadius: '50%', width: 32, height: 32, padding: 0 }} onClick={() => navigate('/provider')} aria-label="Back to Home" title="Back to Home">
            <Icon name="home" />
          </button>
          <span style={{ position: 'relative' }}>
            <span className="avatar green">{member ? initials(member.full_name) : '…'}</span>
            <i style={{ position: 'absolute', right: -1, bottom: -1, width: 10, height: 10, borderRadius: '50%', background: connected ? '#2ecc71' : '#c3d0dc', border: '2px solid #fff' }} />
          </span>
          <div>
            <b style={{ fontSize: 14, display: 'block' }}>{member?.full_name || 'Patient'}</b>
            <small className="slate" style={{ fontSize: 11 }}>{member?.scheme || 'Member'} · <span style={{ color: connected ? '#2ecc71' : 'var(--muted)' }}>{connected ? 'Connected' : 'Connecting…'}</span></small>
          </div>
        </div>
        <button className="btn sm" onClick={handleEnd} disabled={ending}><Icon name="x" /> {ending ? 'Ending…' : 'End Consultation'}</button>
      </div>

      <div style={{ overflowY: 'auto', padding: '20px 16%' }}>
        {(setupError || error) && <div className="notice"><Icon name="alert" /><div>{setupError || error}</div></div>}
        {messages.length === 0 && !setupError && <div style={{ textAlign: 'center', fontSize: 11.5, color: 'var(--slate)', margin: '20px 0' }}>{connected ? 'No messages yet.' : 'Connecting…'}</div>}
        {groups.map((g, gi) => (
          <div key={gi} style={{ margin: '14px 0' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: g.from === 'clinician' ? 'flex-end' : 'flex-start', gap: 3 }}>
              {g.items.map((m, mi) => (
                <div key={m.id} style={{ display: 'flex', flexDirection: 'column', alignItems: g.from === 'clinician' ? 'flex-end' : 'flex-start', maxWidth: '70%' }}>
                  <div style={{
                    background: g.from === 'clinician' ? 'var(--teal-deep)' : '#fff',
                    color: g.from === 'clinician' ? '#fff' : 'inherit',
                    border: g.from === 'clinician' ? 'none' : '1px solid var(--border)',
                    borderRadius: 14,
                    padding: '10px 14px',
                    fontSize: 13.5,
                  }}>{m.text}</div>
                  {mi === g.items.length - 1 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
                      <small className="muted" style={{ fontSize: 10 }}>{fmtTime(m.time)}</small>
                      {g.from === 'clinician' && <span style={{ fontSize: 10, color: m.read ? 'var(--teal-deep)' : 'var(--muted)' }}>✓✓</span>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
        {counterpartTyping && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '6px 0' }}>
            <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 14, padding: '10px 14px', display: 'flex', gap: 4 }}>
              <i className="typing-dot" /><i className="typing-dot" /><i className="typing-dot" />
            </div>
          </div>
        )}
        <div ref={listEndRef} />
      </div>

      <div style={{ background: '#fff', borderTop: '1px solid var(--border)', padding: '10px 16px' }}>
        <div style={{ maxWidth: 720, margin: '0 auto', display: 'flex', alignItems: 'flex-end', gap: 8 }}>
          <div style={{ flex: 1, display: 'flex', alignItems: 'flex-end', border: '1px solid var(--border)', borderRadius: 18, padding: '4px 6px 4px 12px', background: 'var(--bg, #f8fafb)' }}>
            <textarea
              ref={textareaRef}
              rows={1}
              value={draft}
              onChange={(e) => { setDraft(e.target.value); autoResize(); }}
              onKeyDown={handleKeyDown}
              placeholder="Reply to your patient… (Enter to send, Shift+Enter for a new line)"
              disabled={!connected}
              style={{ flex: 1, resize: 'none', border: 'none', background: 'transparent', outline: 'none', fontSize: 13.5, padding: '6px 0', fontFamily: 'inherit', maxHeight: 120 }}
            />
          </div>
          <button className="btn primary" style={{ borderRadius: '50%', width: 38, height: 38, padding: 0, flexShrink: 0 }} onClick={handleSend} disabled={!connected || !draft.trim()} aria-label="Send">
            <Icon name="send" />
          </button>
        </div>
      </div>
    </div>
    </div>
  );
}
