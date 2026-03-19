import React, { useEffect, useMemo, useRef, useState } from 'react';
import ProgressBar from './ProgressBar';
import { fetchHistory, resetChat, sendMessage } from '../api';
import logo from '../assets/logo.png';

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

  const [messages, setMessages]               = useState([defaultWelcome]);
  const [input, setInput]                     = useState('');
  const [loading, setLoading]                 = useState(true);
  const [sending, setSending]                 = useState(false);
  const [sendPhase, setSendPhase]             = useState('');
  const [error, setError]                     = useState('');
  const [session, setSession]                 = useState({
    question_count: 0,
    question_limit: 10,
    questions_remaining: 10,
    limit_reached: false
  });
  const [darkMode, setDarkMode]               = useState(() => {
    return localStorage.getItem('darkMode') === 'true';
  });

  const isMountedRef   = useRef(true);
  const messagesEndRef = useRef(null);
  useEffect(() => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, sending]);

  useEffect(() => {
    return () => { isMountedRef.current = false; };
  }, []);

  useEffect(() => {
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  useEffect(() => {
    let mounted = true;
    async function loadData() {
      setLoading(true);
      setError('');
      try {
        const historyResponse = await fetchHistory();
        if (!mounted) return;
        const parsedHistory = (historyResponse.history || [])
          .map(entry => ({ role: entry.role, content: entry.content, createdAt: entry.created_at }))
          .filter(item => item.content && item.content.trim().length > 0);
        setMessages(parsedHistory.length ? parsedHistory : [defaultWelcome]);
        setSession(prev => ({ ...prev, ...(historyResponse.session || {}) }));
      } catch (err) {
        if (!mounted) return;
        if (err?.status === 401 && typeof onLogout === 'function') { onLogout(); return; }
        setMessages([defaultWelcome]);
        setError('Unable to load your previous chat. You can still start a new conversation.');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadData();
    return () => { mounted = false; };
  }, [defaultWelcome, onLogout, user?.id]);

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || sending) return;
    if (session.limit_reached) {
      setError('You have reached the question limit for this chat. Reset the session to continue.');
      return;
    }
    setMessages(prev => [...prev, { role: 'user', content: trimmed }]);
    setInput('');
    setSending(true);
    setSendPhase('thinking');
    setError('');
    try {
      const response = await sendMessage(trimmed);
      const returnedMessages = response.messages || [];
      const assistantMessage = returnedMessages.find(entry => entry.role === 'assistant');
      const replyText = assistantMessage?.content || '...';
      setMessages(prev => [...prev, assistantMessage || { role: 'assistant', content: replyText }]);
      setSession(prev => ({ ...prev, ...(response.session || {}) }));
    } catch (err) {
      const isAuthError = err?.status === 401;
      const fallback = isAuthError
        ? 'Your session has expired. Please log in again.'
        : err?.payload?.error || err?.message || 'Something went wrong. Please try again.';
      setMessages(prev => [...prev, { role: 'assistant', content: fallback }]);
      setError(fallback);
      if (isAuthError && typeof onLogout === 'function') onLogout();
    } finally {
      setSending(false);
      setSendPhase('');
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  async function handleReset() {
    setError('');
    try {
      await resetChat();
      setMessages([defaultWelcome]);
      setSession({
        question_count: 0,
        question_limit: 10,
        questions_remaining: 10,
        limit_reached: false
      });
    } catch (err) {
      setError(err?.payload?.error || err?.message || 'Unable to reset session.');
    }
  }

  return (
    <div className={`app-wrapper ${darkMode ? 'dark' : 'light'}`}>

  
      <div className="bg-scene">
        {darkMode ? (

    
          <svg className="bg-svg" viewBox="0 0 1440 900" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">

        
            <defs>
              <radialGradient id="moonGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%"   stopColor="#fffde7" stopOpacity="1"/>
                <stop offset="40%"  stopColor="#f9e97e" stopOpacity="1"/>
                <stop offset="100%" stopColor="#f0c040" stopOpacity="1"/>
              </radialGradient>
              <radialGradient id="moonHalo" cx="50%" cy="50%" r="50%">
                <stop offset="0%"   stopColor="#ffe066" stopOpacity="0.35"/>
                <stop offset="100%" stopColor="#ffe066" stopOpacity="0"/>
              </radialGradient>
            </defs>

      
            <circle cx="1260" cy="100" r="90" fill="url(#moonHalo)"/>

       
            <circle cx="1260" cy="100" r="48" fill="url(#moonGlow)"/>

      
            <circle cx="1245" cy="88"  r="7"  fill="#f0c040" opacity="0.5"/>
            <circle cx="1268" cy="115" r="5"  fill="#e6b800" opacity="0.4"/>
            <circle cx="1280" cy="90"  r="4"  fill="#e6b800" opacity="0.35"/>
            <circle cx="1250" cy="108" r="3"  fill="#e6b800" opacity="0.3"/>

     
            <path d="M80,60 L83,70 L93,73 L83,76 L80,86 L77,76 L67,73 L77,70 Z"   fill="white" opacity="0.95"/>
            <path d="M300,40 L303,52 L315,55 L303,58 L300,70 L297,58 L285,55 L297,52 Z" fill="white" opacity="0.9"/>
            <path d="M600,30 L603,42 L615,45 L603,48 L600,60 L597,48 L585,45 L597,42 Z" fill="white" opacity="0.95"/>
            <path d="M900,50 L903,62 L915,65 L903,68 L900,80 L897,68 L885,65 L897,62 Z" fill="white" opacity="0.9"/>
            <path d="M200,150 L203,160 L213,163 L203,166 L200,176 L197,166 L187,163 L197,160 Z" fill="white" opacity="0.85"/>
            <path d="M1100,140 L1103,150 L1113,153 L1103,156 L1100,166 L1097,156 L1087,153 L1097,150 Z" fill="white" opacity="0.9"/>

      
            <path d="M150,100 L152,107 L159,109 L152,111 L150,118 L148,111 L141,109 L148,107 Z" fill="white" opacity="0.8"/>
            <path d="M420,80  L422,87  L429,89  L422,91  L420,98  L418,91  L411,89  L418,87  Z" fill="white" opacity="0.85"/>
            <path d="M700,70  L702,77  L709,79  L702,81  L700,88  L698,81  L691,79  L698,77  Z" fill="white" opacity="0.75"/>
            <path d="M950,90  L952,97  L959,99  L952,101 L950,108 L948,101 L941,99  L948,97  Z" fill="white" opacity="0.8"/>
            <path d="M1150,60 L1152,67 L1159,69 L1152,71 L1150,78 L1148,71 L1141,69 L1148,67 Z" fill="white" opacity="0.85"/>
            <path d="M50,200  L52,207  L59,209  L52,211  L50,218  L48,211  L41,209  L48,207  Z" fill="white" opacity="0.7"/>
            <path d="M350,180 L352,187 L359,189 L352,191 L350,198 L348,191 L341,189 L348,187 Z" fill="white" opacity="0.75"/>
            <path d="M750,160 L752,167 L759,169 L752,171 L750,178 L748,171 L741,169 L748,167 Z" fill="white" opacity="0.8"/>
            <path d="M1050,170 L1052,177 L1059,179 L1052,181 L1050,188 L1048,181 L1041,179 L1048,177 Z" fill="white" opacity="0.7"/>
            <path d="M500,130 L502,137 L509,139 L502,141 L500,148 L498,141 L491,139 L498,137 Z" fill="white" opacity="0.8"/>
            <path d="M1300,80  L1302,87  L1309,89  L1302,91  L1300,98  L1298,91  L1291,89  L1298,87  Z" fill="white" opacity="0.75"/>


            <circle cx="100"  cy="140" r="2" fill="white" opacity="0.6"/>
            <circle cx="250"  cy="90"  r="2" fill="white" opacity="0.7"/>
            <circle cx="460"  cy="50"  r="2" fill="white" opacity="0.65"/>
            <circle cx="650"  cy="120" r="2" fill="white" opacity="0.6"/>
            <circle cx="820"  cy="40"  r="2" fill="white" opacity="0.7"/>
            <circle cx="1000" cy="110" r="2" fill="white" opacity="0.65"/>
            <circle cx="1200" cy="45"  r="2" fill="white" opacity="0.6"/>
            <circle cx="1380" cy="130" r="2" fill="white" opacity="0.7"/>
            <circle cx="170"  cy="220" r="2" fill="white" opacity="0.55"/>
            <circle cx="550"  cy="200" r="2" fill="white" opacity="0.6"/>
            <circle cx="860"  cy="190" r="2" fill="white" opacity="0.55"/>
            <circle cx="1350" cy="200" r="2" fill="white" opacity="0.6"/>
            <circle cx="380"  cy="240" r="1.5" fill="white" opacity="0.5"/>
            <circle cx="680"  cy="250" r="1.5" fill="white" opacity="0.55"/>
            <circle cx="1100" cy="230" r="1.5" fill="white" opacity="0.5"/>
            <circle cx="30"   cy="300" r="1.5" fill="white" opacity="0.45"/>
            <circle cx="780"  cy="280" r="1.5" fill="white" opacity="0.5"/>
            <circle cx="1250" cy="270" r="1.5" fill="white" opacity="0.45"/>
          </svg>

        ) : (

  
        <svg className="bg-svg" viewBox="0 0 1440 900" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">

            {/* Cloud 1 - large left */}
            <g opacity="0.95" filter="drop-shadow(0 8px 16px rgba(0,0,0,0.08))">
              <ellipse cx="180" cy="80"  rx="90"  ry="35" fill="white"/>
              <ellipse cx="130" cy="90"  rx="55"  ry="42" fill="white"/>
              <ellipse cx="210" cy="68"  rx="60"  ry="45" fill="white"/>
              <ellipse cx="265" cy="85"  rx="48"  ry="32" fill="white"/>
              <ellipse cx="155" cy="75"  rx="40"  ry="30" fill="#f0f8ff"/>
            </g>

            <g opacity="0.9" filter="drop-shadow(0 8px 16px rgba(0,0,0,0.07))">
              <ellipse cx="620" cy="55"  rx="80"  ry="28" fill="white"/>
              <ellipse cx="570" cy="65"  rx="50"  ry="38" fill="white"/>
              <ellipse cx="650" cy="45"  rx="55"  ry="40" fill="white"/>
              <ellipse cx="700" cy="60"  rx="42"  ry="28" fill="white"/>
            </g>


            <g opacity="0.85" filter="drop-shadow(0 6px 12px rgba(0,0,0,0.06))">
              <ellipse cx="1050" cy="45" rx="70"  ry="25" fill="white"/>
              <ellipse cx="1005" cy="55" rx="45"  ry="34" fill="white"/>
              <ellipse cx="1080" cy="38" rx="50"  ry="36" fill="white"/>
              <ellipse cx="1125" cy="50" rx="38"  ry="25" fill="white"/>
            </g>

     
            <g opacity="0.8" filter="drop-shadow(0 6px 12px rgba(0,0,0,0.06))">
              <ellipse cx="90"  cy="180" rx="65"  ry="24" fill="white"/>
              <ellipse cx="50"  cy="188" rx="42"  ry="32" fill="white"/>
              <ellipse cx="120" cy="170" rx="48"  ry="35" fill="white"/>
              <ellipse cx="160" cy="182" rx="35"  ry="22" fill="white"/>
            </g>

            <g opacity="0.82" filter="drop-shadow(0 6px 12px rgba(0,0,0,0.06))">
              <ellipse cx="800" cy="150" rx="75"  ry="26" fill="white"/>
              <ellipse cx="755" cy="160" rx="48"  ry="36" fill="white"/>
              <ellipse cx="835" cy="142" rx="52"  ry="38" fill="white"/>
              <ellipse cx="880" cy="155" rx="40"  ry="25" fill="white"/>
            </g>

          </svg>
        )}
      </div>


      <div className={`chatgpt-shell ${darkMode ? 'dark' : 'light'}`}>

 
        <header className={`chatgpt-header ${darkMode ? 'dark' : 'light'}`}>
          <div className="chatgpt-title">
            <h1>Meet Mama Akinyi</h1>
            <p>Your AI learning friend</p>
          </div>
          <div className="chatgpt-controls">
            <button
              className="mode-toggle-btn"
              onClick={() => setDarkMode(!darkMode)}
              title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              <div className={`toggle-track ${darkMode ? 'dark' : 'light'}`}>
                <div className={`toggle-thumb ${darkMode ? 'right' : 'left'}`} />
                <span className="toggle-label">{darkMode ? '🌙' : '☀️'}</span>
              </div>
            </button>
            <button className={`ghost-btn ${darkMode ? 'dark' : 'light'}`} onClick={handleReset} disabled={loading || sending}>
              Reset Session
            </button>
            <button className={`ghost-btn ${darkMode ? 'dark' : 'light'}`} onClick={onLogout} disabled={sending}>
              Logout
            </button>
            <div className={`user-profile ${darkMode ? 'dark' : 'light'}`}>
              <div className="user-avatar">{initials}</div>
              <div className="user-details">
                <span className={`user-name ${darkMode ? 'dark' : 'light'}`}>{displayName}</span>
                <span className="user-status">{loading ? 'Syncing...' : 'Online'}</span>
              </div>
            </div>
          </div>
        </header>

        {/* ── Progress Bar ── */}
        <div className="chatgpt-progress">
          <ProgressBar
            value={Math.min(session.question_count || 0, session.question_limit || 10)}
            max={session.question_limit || 10}
            darkMode={darkMode}
            label="Questions used"
          />
        </div>


        <div className={`chatgpt-body ${darkMode ? 'dark' : 'light'}`}>
          <div className="chatgpt-messages">
            {messages.map((m, idx) => {
              const isAi = m.role === 'assistant';
              return (
                <div key={idx} className={`message-row ${isAi ? 'ai' : 'user'} ${darkMode ? 'dark' : 'light'}`}>
                  <div className="message-avatar">
                    {isAi ? <img src={logo} alt="Mama Akinyi" className="avatar-logo" /> : initials}
                  </div>
                  <div className="message-content">
                    <div className="message-name">{isAi ? 'Mama Akinyi' : displayName}</div>
                    <div className="message-text">{m.content}</div>
                  </div>
                </div>
              );
            })}
            {sending && (
              <div className={`message-row ai ${darkMode ? 'dark' : 'light'}`}>
                <div className="message-avatar">
                  <img src={logo} alt="Mama Akinyi" className="avatar-logo" />
                </div>
                <div className="message-content">
                  <div className="message-name">Mama Akinyi</div>
                  <div className="message-text thinking">
                    <span className="thinking-label">{sendPhase === 'thinking' ? 'Thinking...' : 'Replying...'}</span>
                    <span /><span /><span />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className={`chatgpt-input ${darkMode ? 'dark' : 'light'}`}>
            <div className={`input-bar ${darkMode ? 'dark' : 'light'}`}>
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Send a message..."
                onKeyDown={handleKeyDown}
                rows={1}
                disabled={sending || session.limit_reached}
              />
              <button
                type="button"
                aria-label="Send"
                onClick={handleSend}
                disabled={sending || !input.trim() || session.limit_reached}
              >
                {sending ? '...' : '➤'}
              </button>
            </div>
            {error && <p className="input-error">{error}</p>}
            <p className="input-disclaimer">
              {session.questions_remaining} question{session.questions_remaining === 1 ? '' : 's'} left in this chat.
            </p>
            <p className="input-disclaimer">
              Mama Akinyi may produce inaccurate information about people, places, or facts.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatWindow;
