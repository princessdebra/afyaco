import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Icon from '../components/Icon';
import { initials } from '../components/Brand';
import ConversationList from '../components/ConversationList';
import { api } from '../api/client';
import useChatRoom from '../hooks/useChatRoom';

const SpeechRecognitionImpl = typeof window !== 'undefined' ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null;

function fmtTime(d) {
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

export default function ChatConsultation() {
  const { appointmentId } = useParams();
  const navigate = useNavigate();
  const [provider, setProvider] = useState(null);
  const [consultation, setConsultation] = useState(null);
  const [conversations, setConversations] = useState(null);
  const [setupError, setSetupError] = useState('');
  const [draft, setDraft] = useState('');
  const [recording, setRecording] = useState(false);
  const [micLang, setMicLang] = useState('en-US');
  const [micError, setMicError] = useState('');
  const listEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const textareaRef = useRef(null);

  const { messages, connected, counterpartTyping, error, send, sendTyping, markRead } = useChatRoom(consultation?.id, 'member');

  useEffect(() => {
    api.listMyConversations().then(setConversations).catch(() => setConversations([]));
  }, [appointmentId]);

  useEffect(() => {
    let cancelled = false;
    setConsultation(null);
    setSetupError('');
    (async () => {
      try {
        const [appt, providers] = await Promise.all([api.getAppointment(appointmentId), api.listProviders()]);
        if (cancelled) return;
        setProvider(providers.find((pr) => pr.id === appt.provider_id) || null);
        let c;
        try {
          c = await api.startConsultation(appointmentId);
        } catch {
          // Already ended/cancelled — don't treat that as fatal, fall back to
          // the existing thread so history stays reachable (nothing was ever
          // deleted; there was just no way back in before this fallback).
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

  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, counterpartTyping]);

  useEffect(() => {
    if (messages.some((m) => m.from === 'clinician')) markRead();
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

  function handleComposerKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    } else {
      sendTyping();
    }
  }

  function toggleMic() {
    if (!SpeechRecognitionImpl) {
      setMicError('Voice input is not supported in this browser — try Chrome.');
      return;
    }
    if (recording) {
      recognitionRef.current?.stop();
      return;
    }
    const rec = new SpeechRecognitionImpl();
    rec.lang = micLang;
    rec.interimResults = true;
    rec.continuous = true;
    rec.onresult = (ev) => {
      let finalText = '';
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        if (ev.results[i].isFinal) finalText += ev.results[i][0].transcript;
      }
      if (finalText) setDraft((d) => `${d}${d && !d.endsWith(' ') ? ' ' : ''}${finalText.trim()} `);
      requestAnimationFrame(autoResize);
    };
    rec.onerror = (ev) => setMicError(ev.error === 'not-allowed' ? 'Microphone access was blocked — check browser permissions.' : 'Voice input stopped unexpectedly.');
    rec.onend = () => setRecording(false);
    recognitionRef.current = rec;
    setMicError('');
    setRecording(true);
    rec.start();
  }

  // Group consecutive same-sender messages so repeats don't look automated.
  const groups = [];
  for (const m of messages) {
    const last = groups[groups.length - 1];
    if (last && last.from === m.from) last.items.push(m);
    else groups.push({ from: m.from, items: [m] });
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'var(--bg, #f4f8f7)', zIndex: 1000, display: 'flex' }}>
    <ConversationList conversations={conversations} activeAppointmentId={appointmentId} basePath="/portal/chat" />
    <div style={{ flex: 1, minWidth: 0, display: 'grid', gridTemplateRows: 'auto 1fr auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 20px', background: '#fff', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button className="btn sm" style={{ borderRadius: '50%', width: 32, height: 32, padding: 0 }} onClick={() => navigate('/portal')} aria-label="Back to Home" title="Back to Home">
            <Icon name="home" />
          </button>
          <span style={{ position: 'relative' }}>
            <span className="avatar green">{provider ? initials(provider.name) : '…'}</span>
            <i style={{ position: 'absolute', right: -1, bottom: -1, width: 10, height: 10, borderRadius: '50%', background: connected ? '#2ecc71' : '#c3d0dc', border: '2px solid #fff' }} />
          </span>
          <div>
            <b style={{ fontSize: 14, display: 'block' }}>{provider?.name || 'Consultation'}</b>
            <small className="slate" style={{ fontSize: 11 }}>
              {provider?.specialties?.[0] || 'Clinician'} · <span style={{ color: connected ? '#2ecc71' : 'var(--muted)' }}>{connected ? 'Connected' : 'Connecting…'}</span>
            </small>
          </div>
        </div>
      </div>

      <div style={{ overflowY: 'auto', padding: '20px 16%' }}>
        {(setupError || error) && <div className="notice"><Icon name="alert" /><div>{setupError || error}</div></div>}
        {messages.length === 0 && !setupError && <div style={{ textAlign: 'center', fontSize: 11.5, color: 'var(--slate)', margin: '20px 0' }}>{connected ? 'Say hello to get started.' : 'Connecting to your clinician…'}</div>}
        {groups.map((g, gi) => (
          <div key={gi} style={{ margin: '14px 0' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: g.from === 'member' ? 'flex-end' : 'flex-start', gap: 3 }}>
              {g.items.map((m, mi) => (
                <div key={m.id} style={{ display: 'flex', flexDirection: 'column', alignItems: g.from === 'member' ? 'flex-end' : 'flex-start', maxWidth: '70%' }}>
                  <div style={{
                    background: g.from === 'member' ? 'var(--teal-deep)' : '#fff',
                    color: g.from === 'member' ? '#fff' : 'inherit',
                    border: g.from === 'member' ? 'none' : '1px solid var(--border)',
                    borderRadius: 14,
                    padding: '10px 14px',
                    fontSize: 13.5,
                  }}>{m.text}</div>
                  {mi === g.items.length - 1 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
                      <small className="muted" style={{ fontSize: 10 }}>{fmtTime(m.time)}</small>
                      {g.from === 'member' && (
                        <span style={{ fontSize: 10, color: m.read ? 'var(--teal-deep)' : 'var(--muted)' }}>✓✓</span>
                      )}
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
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
        {micError && <small style={{ color: 'var(--warn-orange, #c0392b)', display: 'block', marginBottom: 6 }}>{micError}</small>}
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
          <div style={{ flex: 1, display: 'flex', alignItems: 'flex-end', border: '1px solid var(--border)', borderRadius: 18, padding: '4px 6px 4px 12px', background: 'var(--bg, #f8fafb)' }}>
            <textarea
              ref={textareaRef}
              rows={1}
              value={draft}
              onChange={(e) => { setDraft(e.target.value); autoResize(); }}
              onKeyDown={handleComposerKeyDown}
              placeholder="Type a message… (Enter to send, Shift+Enter for a new line)"
              disabled={!connected}
              style={{ flex: 1, resize: 'none', border: 'none', background: 'transparent', outline: 'none', fontSize: 13.5, padding: '6px 0', fontFamily: 'inherit', maxHeight: 120 }}
            />
            <button
              type="button"
              className="btn sm"
              style={{ borderRadius: '50%', width: 30, height: 30, padding: 0, flexShrink: 0, background: recording ? '#e8365d' : undefined, borderColor: recording ? '#e8365d' : undefined, color: recording ? '#fff' : undefined }}
              onClick={toggleMic}
              aria-label={recording ? 'Stop recording' : 'Start voice input'}
              title={recording ? 'Stop recording' : 'Voice input'}
            >
              <Icon name={recording ? 'micOff' : 'mic'} />
            </button>
            <button
              type="button"
              className="btn sm"
              style={{ borderRadius: 14, padding: '0 8px', height: 30, flexShrink: 0, fontSize: 10.5 }}
              onClick={() => setMicLang((l) => (l === 'en-US' ? 'sw-KE' : 'en-US'))}
              title="Voice input language"
            >
              <Icon name="globe" /> {micLang === 'en-US' ? 'EN' : 'SW'}
            </button>
          </div>

          <button className="btn primary" style={{ borderRadius: '50%', width: 38, height: 38, padding: 0, flexShrink: 0 }} onClick={handleSend} disabled={!connected || !draft.trim()} aria-label="Send">
            <Icon name="send" />
          </button>
        </div>
        </div>
      </div>
    </div>
    </div>
  );
}
