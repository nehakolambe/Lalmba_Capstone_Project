import React, { useEffect, useMemo, useRef, useState } from 'react';
import ProgressBar from './ProgressBar';
import { fetchHistory, fetchProgress, recordProgress, resetChat, sendMessage } from '../api';

function ChatWindow({ user, onLogout }) {
  const displayName = useMemo(() => (user?.username || 'Guest').trim() || 'Guest', [user]);
  const initials = displayName.charAt(0).toUpperCase();

  const defaultWelcome = useMemo(
    () => ({
      role: 'assistant',
      content: `Hello ${displayName}! Mama Akinyi is here to help. How can I assist you today?`
    }),
    [displayName]
  );

  const [messages, setMessages] = useState([defaultWelcome]);
  const [input, setInput] = useState('');
  const [progressEntries, setProgressEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const isMountedRef = useRef(true);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const maxProgress = 10;

  useEffect(() => {
    let mounted = true;

    async function loadData() {
      setLoading(true);
      setError('');
      try {
        const [history, progress] = await Promise.all([fetchHistory(), fetchProgress()]);

        if (!mounted) return;

        const parsedHistory = history
          .map(entry => ({
            role: entry.role,
            content: entry.content,
            createdAt: entry.created_at
          }))
          .filter(item => item.content && item.content.trim().length > 0);

        setMessages(parsedHistory.length ? parsedHistory : [defaultWelcome]);
        setProgressEntries(progress);
      } catch (err) {
        if (!mounted) return;
        if (err?.status === 401 && typeof onLogout === 'function') {
          onLogout();
          return;
        }
        setMessages([defaultWelcome]);
        setError('Unable to load your previous chat. You can still start a new conversation.');
      } finally {
        if (mounted) setLoading(false);
      }
    }

    loadData();

    return () => {
      mounted = false;
    };
  }, [defaultWelcome, onLogout, user?.id]);

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    const userMsg = { role: 'user', content: trimmed };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setSending(true);
    setError('');

    try {
      const returned = await sendMessage(trimmed);
      const assistantMessage = returned.find(entry => entry.role === 'assistant');
      const replyText = assistantMessage?.content || '...';

      if (assistantMessage) {
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: replyText }]);
      }

      if (progressEntries.length < maxProgress) {
        try {
          const milestone = `Reflection ${progressEntries.length + 1}`;
          const notes = replyText.slice(0, 200) || 'Continued guidance from Mama Akinyi.';
          const newEntry = await recordProgress(milestone, notes);
          setProgressEntries(prev => [...prev, newEntry]);
        } catch (progressErr) {
          console.warn('Failed to record progress:', progressErr);
        }
      }
    } catch (err) {
      const isAuthError = err?.status === 401;
      let fallback = '';
      if (isAuthError) {
        fallback = 'Your session has expired. Please log in again.';
      } else if (err?.network || err?.message === 'Cannot connect to server') {
        fallback =
          'Cannot reach the Matoso server. Confirm Flask is running on http://localhost:5000 and refresh this page.';
      } else {
        fallback = err?.payload?.error || err?.message || 'Something went wrong. Please try again.';
      }

      setMessages(prev => [...prev, { role: 'assistant', content: fallback }]);
      setError(fallback);
      if (isAuthError && typeof onLogout === 'function') {
        onLogout();
      }
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  async function handleReset() {
    setError('');
    try {
      await resetChat();
      setMessages([defaultWelcome]);
      setProgressEntries([]);
    } catch (err) {
      const message = err?.payload?.error || err?.message || 'Unable to reset chat history.';
      setError(message);
    }
  }

  return (
    <div className="chatgpt-shell">
      <header className="chatgpt-header">
        <div className="chatgpt-title">
          <h1>Chat Session</h1>
          <p>Powered by Mama Akinyi</p>
        </div>
        <div className="chatgpt-controls">
          <button className="ghost-btn" onClick={handleReset} disabled={loading || sending}>
            Reset chat
          </button>
          <button className="ghost-btn" onClick={onLogout} disabled={sending}>
            Logout
          </button>
          <div className="user-profile" aria-label="User profile">
            <div className="user-avatar" aria-hidden="true">{initials}</div>
            <div className="user-details">
              <span className="user-name">{displayName}</span>
              <span className="user-status">{loading ? 'Syncing...' : 'Online'}</span>
            </div>
          </div>
        </div>
      </header>

      <div className="chatgpt-progress">
        <ProgressBar value={Math.min(progressEntries.length, maxProgress)} max={maxProgress} />
      </div>

      <div className="chatgpt-body">
        <div className="chatgpt-messages">
          {messages.map((m, idx) => {
            const isAi = m.role === 'assistant';
            const avatarLabel = isAi ? 'AI' : initials;
            const nameLabel = isAi ? 'Mama Akinyi' : displayName;

            return (
              <div key={idx} className={`message-row ${isAi ? 'ai' : 'user'}`}>
                <div className="message-avatar">{avatarLabel}</div>
                <div className="message-content">
                  <div className="message-name">{nameLabel}</div>
                  <div className="message-text">{m.content}</div>
                </div>
              </div>
            );
          })}
          {sending && (
            <div className="message-row ai">
              <div className="message-avatar">AI</div>
              <div className="message-content">
                <div className="message-name">Mama Akinyi</div>
                <div className="message-text">Thinking...</div>
              </div>
            </div>
          )}
        </div>
        <div className="chatgpt-input">
          <div className="input-bar">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Send a message."
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={sending}
            />
            <button type="button" onClick={handleSend} disabled={sending || !input.trim()}>
              {sending ? 'Sending...' : 'Send'}
            </button>
          </div>
          {error && <p className="input-error">{error}</p>}
          <p className="input-disclaimer">
            Mama Akinyi may produce inaccurate information about people, places, or facts.
          </p>
        </div>
      </div>
    </div>
  );
}

export default ChatWindow;
