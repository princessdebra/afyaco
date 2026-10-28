import { useEffect, useRef, useState } from 'react';
import { api, notificationsWsUrl } from '../api/client';

// One of these lives at the top of each portal layout — keeps a live
// WebSocket open for the whole session so a new chat message or appointment
// reminder shows up (bell badge + toast) no matter which page you're on,
// not just while a chat screen happens to be open.
export default function useNotifications() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [toasts, setToasts] = useState([]);
  const wsRef = useRef(null);

  async function refresh() {
    try {
      const [list, count] = await Promise.all([api.listNotifications(), api.getUnreadCount()]);
      setNotifications(list);
      setUnreadCount(count.count);
    } catch {
      // quiet — the bell just stays at whatever it last knew
    }
  }

  useEffect(() => {
    refresh();
    const ws = new WebSocket(notificationsWsUrl());
    wsRef.current = ws;
    ws.onmessage = (evt) => {
      const data = JSON.parse(evt.data);
      if (data.type !== 'notification') return;
      const n = {
        id: data.id,
        type: data.notification_type,
        title: data.title,
        body: data.body,
        link: data.link,
        created_at: data.created_at,
        read_at: null,
      };
      setNotifications((ns) => [n, ...ns]);
      setUnreadCount((c) => c + 1);
      setToasts((ts) => [...ts, n]);
      setTimeout(() => setToasts((ts) => ts.filter((t) => t.id !== n.id)), 6000);
    };
    return () => ws.close();
  }, []);

  const unreadChatCount = notifications.filter((n) => n.type === 'chat_message' && !n.read_at).length;

  async function markRead(id) {
    setNotifications((ns) => ns.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n)));
    setUnreadCount((c) => Math.max(0, c - 1));
    try { await api.markNotificationRead(id); } catch { /* best-effort */ }
  }

  async function markAllRead() {
    setNotifications((ns) => ns.map((n) => ({ ...n, read_at: n.read_at || new Date().toISOString() })));
    setUnreadCount(0);
    try { await api.markAllNotificationsRead(); } catch { /* best-effort */ }
  }

  function dismissToast(id) {
    setToasts((ts) => ts.filter((t) => t.id !== id));
  }

  return { notifications, unreadCount, unreadChatCount, toasts, markRead, markAllRead, dismissToast };
}
