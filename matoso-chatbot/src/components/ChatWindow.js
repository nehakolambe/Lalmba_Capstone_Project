import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchHistory, incrementProgress, resetChat, sendMessage } from '../api';
import QuickReplies from './QuickReplies';
import StartCards from './StartCards';
import TypingPractice from './TypingPractice';

const HELP_TEXT = "I don't know how to use the keyboard and mouse. Help me.";

function ChatWindow({ user, onLogout, onHome, pendingPrompt, launchTypingPractice, onStarterConsumed }) {
  const displayName = useMemo(
    () => (user?.full_name || user?.username || 'Guest').trim() || 'Guest',
    [user]
  );
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
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);
  const [typingPracticeOpen, setTypingPracticeOpen] = useState(false);
  const [speakingIndex, setSpeakingIndex] = useState(null);
  const [speechSupported, setSpeechSupported] = useState(false);
  const autoSentRef = useRef(new Set());

  useEffect(() => {
    setSpeechSupported(typeof window !== 'undefined' && 'speechSynthesis' in window);
    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  useEffect(() => {
    let mounted = true;

    async function loadData() {
      setLoading(true);
      setError('');
      try {
        const history = await fetchHistory();

        if (!mounted) return;

        const parsedHistory = history
          .map(entry => ({
            role: entry.role,
            content: entry.content,
            createdAt: entry.created_at
          }))
          .filter(item => item.content && item.content.trim().length > 0);

        setMessages(parsedHistory.length ? parsedHistory : [defaultWelcome]);
      } catch (err) {
        if (!mounted) return;
        if (err?.status === 401 && typeof onLogout === 'function') {
          onLogout();
          return;
        }
        setMessages([defaultWelcome]);
        const message =
          err?.payload?.error ||
          err?.payload?.message ||
          err?.message ||
          'Unable to load your previous chat. You can still start a new conversation.';
        setError(message);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    loadData();

    return () => {
      mounted = false;
    };
  }, [defaultWelcome, onLogout, user?.id]);


  const sendText = useCallback(
    async (rawText, { clearInput = true, openTypingPractice = false } = {}) => {
      const trimmed = (rawText || '').trim();
      if (!trimmed || sending) return;

      if (openTypingPractice) {
        setTypingPracticeOpen(true);
      }

      const userMsg = { role: 'user', content: trimmed };
      setMessages(prev => [...prev, userMsg]);
      if (clearInput) setInput('');
      setSending(true);
      setError('');

      try {
        const { messages: returnedMessages, sources } = await sendMessage(trimmed);
        const normalizedMessages = (returnedMessages || []).map(entry => ({
          role: entry.role,
          content: entry.content,
          createdAt: entry.created_at
        }));
        const assistantIndex = normalizedMessages.findIndex(entry => entry.role === 'assistant');
        if (assistantIndex >= 0) {
          normalizedMessages[assistantIndex] = {
            ...normalizedMessages[assistantIndex],
            sources
          };
        } else {
          normalizedMessages.push({
            role: 'assistant',
            content: '...',
            sources
          });
        }

        setMessages(prev => {
          const last = prev[prev.length - 1];
          const base =
            last && last.role === 'user' && last.content === userMsg.content
              ? prev.slice(0, -1)
              : prev;
          return [...base, ...normalizedMessages];
        });

        try {
          await incrementProgress();
        } catch (progressErr) {
          console.warn('Failed to update progress:', progressErr);
        }
      } catch (err) {
        const isAuthError = err?.status === 401;
        let fallback = '';
        if (isAuthError) {
          fallback = 'Your session has expired. Please log in again.';
        } else if (err?.network || err?.message === 'Cannot connect to server') {
          fallback =
            'Cannot reach the Matoso server. Confirm Flask is running on http://127.0.0.1:5000 and refresh this page.';
        } else {
          fallback =
            err?.payload?.error ||
            err?.payload?.message ||
            err?.message ||
            'Something went wrong. Please try again.';
        }

        if (err?.status === 503) {
          const detail = err?.payload?.details?.reason;
          const hint = 'Make sure Ollama is running and the model is installed.';
          fallback = detail ? `${fallback} Reason: ${detail}. ${hint}` : `${fallback} ${hint}`;
        }

        setMessages(prev => [...prev, { role: 'assistant', content: fallback }]);
        setError(fallback);
        if (isAuthError && typeof onLogout === 'function') {
          onLogout();
        }
      } finally {
        setSending(false);
        if (inputRef.current) inputRef.current.focus();
      }
    },
    [onLogout, sending]
  );

  const handleSend = useCallback(() => {
    if (!input.trim()) return;
    sendText(input, { clearInput: true });
  }, [input, sendText]);

  const handleQuickReply = useCallback(
    text => {
      sendText(text, { clearInput: false });
    },
    [sendText]
  );

  const handleHelp = useCallback(() => {
    sendText(HELP_TEXT, { clearInput: false });
  }, [sendText]);

  const handleStartCard = useCallback(
    card => {
      if (!card?.prompt) return;
      sendText(card.prompt, { clearInput: true, openTypingPractice: Boolean(card.typingPractice) });
    },
    [sendText]
  );

  useEffect(() => {
    if (loading) return;
    if (!pendingPrompt) return;
    if (autoSentRef.current.has(pendingPrompt)) return;
    autoSentRef.current.add(pendingPrompt);
    sendText(pendingPrompt, { clearInput: true, openTypingPractice: Boolean(launchTypingPractice) });
    if (typeof onStarterConsumed === 'function') {
      onStarterConsumed();
    }
  }, [loading, pendingPrompt, launchTypingPractice, onStarterConsumed, sendText]);

  useEffect(() => {
    if (launchTypingPractice) {
      setTypingPracticeOpen(true);
    }
  }, [launchTypingPractice]);

  const stopSpeaking = useCallback(() => {
    if (!speechSupported) return;
    window.speechSynthesis.cancel();
    setSpeakingIndex(null);
  }, [speechSupported]);

  const handleSpeakToggle = useCallback(
    (index, text) => {
      if (!speechSupported) return;
      if (speakingIndex === index) {
        stopSpeaking();
        return;
      }
      stopSpeaking();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.onend = () => setSpeakingIndex(null);
      utterance.onerror = () => setSpeakingIndex(null);
      window.speechSynthesis.speak(utterance);
      setSpeakingIndex(index);
    },
    [speechSupported, speakingIndex, stopSpeaking]
  );

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
    } catch (err) {
      const message =
        err?.payload?.error ||
        err?.payload?.message ||
        err?.message ||
        'Unable to reset chat history.';
      setError(message);
    }
  }

  const isEmpty =
    messages.length === 1 &&
    messages[0].role === 'assistant' &&
    messages[0].content === defaultWelcome.content;

  return (
    <div className="chatgpt-shell">
      <header className="chatgpt-header">
        <div className="chatgpt-title">
          <h1>Chat Session</h1>
          <p>Powered by Mama Akinyi</p>
        </div>
        <div className="chatgpt-controls">
          <button className="ghost-btn" onClick={onHome} disabled={sending}>
            Home
          </button>
          <button className="ghost-btn" onClick={handleReset} disabled={loading || sending}>
            Reset chat
          </button>
          <button className="ghost-btn help-btn" onClick={handleHelp} disabled={sending}>
            Help
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

      <div className="chatgpt-body">
        <div className="chatgpt-messages">
          {isEmpty && (
            <div className="chatgpt-empty">
              <div className="empty-title">Start your first chat</div>
              <div className="empty-subtitle">Tap a card to begin.</div>
              <StartCards onSelect={handleStartCard} />
            </div>
          )}
          {messages.map((m, idx) => {
            const isAi = m.role === 'assistant';
            const avatarLabel = isAi ? 'AI' : initials;
            const nameLabel = isAi ? 'Mama Akinyi' : displayName;
            const timestamp = m.createdAt ? new Date(m.createdAt) : new Date();
            const timeLabel = Number.isNaN(timestamp.getTime())
              ? ''
              : timestamp.toLocaleString();

            return (
              <div key={idx} className={`message-row ${isAi ? 'ai' : 'user'}`}>
                <div className="message-avatar">{avatarLabel}</div>
                <div className="message-content">
                  <div className="message-name">{nameLabel}</div>
                  <div className={`message-bubble ${isAi ? 'ai' : 'user'}`}>
                    <div className="message-text">{m.content}</div>
                    {timeLabel && <div className="message-time">{timeLabel}</div>}
                  </div>
                  {isAi && speechSupported && (
                    <div className="message-actions">
                      <button
                        type="button"
                        className="speak-btn"
                        onClick={() => handleSpeakToggle(idx, m.content)}
                      >
                        {speakingIndex === idx ? 'Stop' : '🔊 Read aloud'}
                      </button>
                    </div>
                  )}
                  {isAi && Array.isArray(m.sources) && m.sources.length > 0 && (
                    <div className="message-sources">
                      <div className="message-sources-title">Sources</div>
                      {m.sources.map((source, sourceIndex) => (
                        <div key={`${source.id}-${sourceIndex}`} className="message-source">
                          <strong>[{sourceIndex + 1}]</strong>{' '}
                          {source.app ? `${source.app}: ` : ''}
                          {source.snippet}
                          {source.source_path && (
                            <span className="message-source-path"> ({source.source_path})</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {sending && (
            <div className="message-row ai">
              <div className="message-avatar">AI</div>
              <div className="message-content">
                <div className="message-name">Mama Akinyi</div>
                <div className="message-bubble ai">
                  <div className="message-text">Thinking...</div>
                </div>
              </div>
            </div>
          )}
        </div>
        <TypingPractice
          open={typingPracticeOpen}
          displayName={displayName}
          onClose={() => setTypingPracticeOpen(false)}
          onSendProgress={text => sendText(text, { clearInput: false })}
        />
        <div className="chatgpt-input">
          {sending && <div className="typing-indicator">Mama Akinyi is typing…</div>}
          <QuickReplies
            onSelect={handleQuickReply}
            hidden={input.trim().length > 0}
            disabled={sending}
          />
          <div className="input-bar">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Send a message."
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={sending}
            />
            <button type="button" onClick={handleSend} disabled={sending || !input.trim()}>
              {sending ? (
                <>
                  <span className="spinner" aria-hidden="true" /> Sending…
                </>
              ) : (
                'Send'
              )}
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
