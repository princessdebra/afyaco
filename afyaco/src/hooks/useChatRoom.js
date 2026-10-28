import { useEffect, useRef, useState } from 'react';
import { api, chatWsUrl } from '../api/client';

// Real two-way chat over a WebSocket — shared by the member (ChatConsultation)
// and provider (ProviderChat) pages. Every send is echoed back by the server
// to everyone in the room (sender included), so there's one source of truth
// for message state instead of each side optimistically rendering its own.
export default function useChatRoom(consultationId, myRole) {
  const [messages, setMessages] = useState([]);
  const [connected, setConnected] = useState(false);
  const [counterpartTyping, setCounterpartTyping] = useState(false);
  const [error, setError] = useState('');
  const wsRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  useEffect(() => {
    if (!consultationId) return;
    let cancelled = false;
    let ws;

    (async () => {
      try {
        const history = await api.getChatMessages(consultationId);
        if (cancelled) return;
        setMessages(history.map((m) => ({ id: m.id, from: m.sender_role, text: m.body, time: new Date(m.created_at), read: Boolean(m.read_at) })));
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load chat history.');
      }

      ws = new WebSocket(chatWsUrl(consultationId));
      wsRef.current = ws;
      ws.onopen = () => !cancelled && setConnected(true);
      ws.onclose = () => !cancelled && setConnected(false);
      ws.onerror = () => !cancelled && setError('Chat connection lost — messages may not send until this reconnects.');
      ws.onmessage = (evt) => {
        if (cancelled) return;
        const data = JSON.parse(evt.data);
        if (data.type === 'message') {
          setMessages((ms) => [...ms, { id: data.id, from: data.sender_role, text: data.body, time: new Date(data.created_at), read: false }]);
          if (data.sender_role !== myRole) setCounterpartTyping(false);
        } else if (data.type === 'typing') {
          if (data.sender_role === myRole) return;
          setCounterpartTyping(true);
          clearTimeout(typingTimeoutRef.current);
          typingTimeoutRef.current = setTimeout(() => setCounterpartTyping(false), 3000);
        } else if (data.type === 'read') {
          if (data.reader_role === myRole) return;
          setMessages((ms) => ms.map((m) => (m.from === myRole ? { ...m, read: true } : m)));
        }
      };
    })();

    return () => {
      cancelled = true;
      clearTimeout(typingTimeoutRef.current);
      ws?.close();
    };
  }, [consultationId, myRole]);

  function send(text) {
    const body = text.trim();
    if (!body || wsRef.current?.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: 'message', body }));
  }

  function sendTyping() {
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify({ type: 'typing' }));
  }

  function markRead() {
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify({ type: 'read' }));
  }

  return { messages, connected, counterpartTyping, error, send, sendTyping, markRead };
}
