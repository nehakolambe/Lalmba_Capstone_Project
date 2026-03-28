import React, { useEffect, useMemo, useRef, useState } from 'react';
import ChatSidebar from './ChatSidebar';
import ProgressBar from './ProgressBar';
import {
  createThread,
  deleteThread,
  fetchHistory,
  fetchThreads,
  renameThread,
  resetChat,
  sendMessageStream
} from '../api';
import logo from '../assets/logo.png';

const MAX_INPUT_HEIGHT = 160;

function repairMojibake(text) {
  if (typeof text !== 'string' || !/[ÃÂâ]/.test(text)) {
    return text;
  }

  const suspiciousCharCount = value => (value.match(/[ÃÂâ]/g) || []).length;

  try {
    const bytes = Uint8Array.from(Array.from(text, char => char.charCodeAt(0) & 0xff));
    const repaired = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    if (!repaired.includes('\u0000') && suspiciousCharCount(repaired) < suspiciousCharCount(text)) {
      return repaired;
    }
  } catch {
    // Fall through to targeted replacements below.
  }

  return text
    .replace(/â¯/g, ' ')
    .replace(/Â°/g, '°')
    .replace(/Â/g, '')
    .replace(/â/g, "'")
    .replace(/â/g, '"')
    .replace(/â/g, '"')
    .replace(/â/g, '–')
    .replace(/â/g, '—');
}

function renderInlineFormatting(text) {
  const parts = [];
  const pattern = /\*\*(.+?)\*\*/g;
  let lastIndex = 0;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push(<strong key={`bold-${match.index}`}>{match[1]}</strong>);
    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length ? parts : text;
}

function MessageBody({ content }) {
  const normalized = repairMojibake(content || '');
  const lines = normalized.split('\n');
  const nodes = [];
  let listItems = [];

  function flushList(keyBase) {
    if (!listItems.length) return;
    nodes.push(
      <ol key={`list-${keyBase}`} className="message-list">
        {listItems.map(item => (
          <li key={item.key}>{renderInlineFormatting(item.text)}</li>
        ))}
      </ol>
    );
    listItems = [];
  }

  lines.forEach((line, index) => {
    const orderedMatch = line.match(/^\s*(\d+)\.\s+(.*)$/);
    if (orderedMatch) {
      listItems.push({ key: `item-${index}`, text: orderedMatch[2] });
      return;
    }

    flushList(index);

    if (!line.trim()) {
      nodes.push(<div key={`spacer-${index}`} className="message-spacer" />);
      return;
    }

    nodes.push(
      <p key={`line-${index}`} className="message-paragraph">
        {renderInlineFormatting(line)}
      </p>
    );
  });

  flushList('final');
  return <>{nodes}</>;
}

function sortThreads(list) {
  return [...list].sort((left, right) => {
    const leftTime = Date.parse(left.updated_at || left.created_at || 0);
    const rightTime = Date.parse(right.updated_at || right.created_at || 0);
    return rightTime - leftTime;
  });
}

function buildRecoveredThreadTitle(history = []) {
  const firstUserMessage = history.find(entry => entry.role === 'user' && entry.content?.trim());
  if (!firstUserMessage) return '';
  const cleaned = firstUserMessage.content.trim().replace(/\s+/g, ' ');
  if (!cleaned) return '';
  return cleaned.length <= 255 ? cleaned : cleaned.slice(0, 255).trim();
}

function activeThreadStorageKey(userId) {
  return userId ? `activeThreadId:${userId}` : 'activeThreadId';
}

function ChatWindow({ user, onLogout, onEditProfile }) {
  const displayName = useMemo(() => (user?.username || 'Guest').trim() || 'Guest', [user]);
  const welcomeName = useMemo(
    () => (user?.full_name || user?.username || 'Guest').trim() || 'Guest',
    [user]
  );
  const initials = displayName.charAt(0).toUpperCase();

  const [messages, setMessages]               = useState([]);
  const [threads, setThreads]                 = useState([]);
  const [activeThreadId, setActiveThreadId]   = useState(null);
  const [input, setInput]                     = useState('');
  const [loadingThreads, setLoadingThreads]   = useState(true);
  const [loading, setLoading]                 = useState(true);
  const [sending, setSending]                 = useState(false);
  const [creatingThread, setCreatingThread]   = useState(false);
  const [threadBusyId, setThreadBusyId]       = useState(null);
  const [renamingThreadId, setRenamingThreadId] = useState(null);
  const [renameValue, setRenameValue]         = useState('');
  const [sendPhase, setSendPhase]             = useState('');
  const [streamingReplyStarted, setStreamingReplyStarted] = useState(false);
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

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = 'auto';
    const nextHeight = Math.min(textarea.scrollHeight, MAX_INPUT_HEIGHT);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > MAX_INPUT_HEIGHT ? 'auto' : 'hidden';
  }, [input, activeThreadId]);

  useEffect(() => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, sending]);

  useEffect(() => {
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  useEffect(() => {
    const storageKey = activeThreadStorageKey(user?.id);
    if (activeThreadId) {
      localStorage.setItem(storageKey, String(activeThreadId));
      return;
    }
    localStorage.removeItem(storageKey);
  }, [activeThreadId, user?.id]);

  useEffect(() => {
    let mounted = true;
    async function loadThreadsForUser() {
      setLoadingThreads(true);
      setError('');
      try {
        const loadedThreads = sortThreads(await fetchThreads());
        if (!mounted) return;
        setThreads(loadedThreads);
        const savedActiveId = Number(localStorage.getItem(activeThreadStorageKey(user?.id)));
        setActiveThreadId(prevActiveId => {
          if (prevActiveId && loadedThreads.some(thread => thread.id === prevActiveId)) {
            return prevActiveId;
          }
          if (savedActiveId && loadedThreads.some(thread => thread.id === savedActiveId)) {
            return savedActiveId;
          }
          return loadedThreads[0]?.id ?? null;
        });
      } catch (err) {
        if (!mounted) return;
        if (err?.status === 401 && typeof onLogout === 'function') {
          onLogout();
          return;
        }
        setThreads([]);
        setActiveThreadId(null);
        setMessages([]);
        setError('Unable to load your chats right now. Please try again.');
      } finally {
        if (mounted) setLoadingThreads(false);
      }
    }
    loadThreadsForUser();
    return () => { mounted = false; };
  }, [onLogout, user?.id]);

  useEffect(() => {
    let mounted = true;

    if (!activeThreadId) {
      setLoading(false);
      setMessages([]);
      setSession({
        question_count: 0,
        question_limit: 10,
        questions_remaining: 10,
        limit_reached: false
      });
      return () => { mounted = false; };
    }

    async function loadThreadData() {
      setLoading(true);
      setError('');
      try {
        const historyResponse = await fetchHistory(activeThreadId);
        if (!mounted) return;
        let resolvedThread = historyResponse.thread || null;
        const recoveredTitle =
          resolvedThread?.title === 'New chat'
            ? buildRecoveredThreadTitle(historyResponse.history || [])
            : '';
        if (resolvedThread?.id && recoveredTitle) {
          try {
            resolvedThread = await renameThread(resolvedThread.id, recoveredTitle);
            upsertThread(resolvedThread);
          } catch {
            // Keep the loaded thread if auto-recovery fails.
          }
        }
        const parsedHistory = (historyResponse.history || [])
          .map(entry => ({
            id: entry.id,
            role: entry.role,
            content: entry.content,
            createdAt: entry.created_at
          }))
          .filter(item => item.content && item.content.trim().length > 0);
        setMessages(parsedHistory);
        setSession(prev => ({ ...prev, ...(historyResponse.session || {}) }));
        if (resolvedThread) {
          upsertThread(resolvedThread);
        }
      } catch (err) {
        if (!mounted) return;
        if (err?.status === 401 && typeof onLogout === 'function') {
          onLogout();
          return;
        }
        setMessages([]);
        setError('Unable to load this chat. You can still start a new conversation.');
      } finally {
        if (mounted) setLoading(false);
      }
    }

    loadThreadData();
    return () => { mounted = false; };
  }, [activeThreadId, onLogout]);

  function upsertThread(thread) {
    if (!thread) return;
    setThreads(prevThreads => sortThreads([
      thread,
      ...prevThreads.filter(existingThread => existingThread.id !== thread.id)
    ]));
  }

  async function handleCreateThread() {
    if (creatingThread) return;
    setCreatingThread(true);
    setError('');
    setRenamingThreadId(null);
    try {
      const thread = await createThread();
      upsertThread(thread);
      setActiveThreadId(thread.id);
      setMessages([]);
      setInput('');
    } catch (err) {
      if (err?.status === 401 && typeof onLogout === 'function') {
        onLogout();
        return;
      }
      setError(err?.payload?.error || err?.message || 'Unable to create a new chat.');
    } finally {
      setCreatingThread(false);
    }
  }

  function handleSelectThread(threadId) {
    if (threadId === activeThreadId || sending) return;
    setError('');
    setRenamingThreadId(null);
    setActiveThreadId(threadId);
  }

  function handleStartRename(thread) {
    setRenamingThreadId(thread.id);
    setRenameValue(thread.title);
    setError('');
  }

  async function handleRenameThread(threadId) {
    const nextTitle = renameValue.trim();
    if (!nextTitle) {
      setError('Chat title cannot be empty.');
      return;
    }

    setThreadBusyId(threadId);
    setError('');
    try {
      const updatedThread = await renameThread(threadId, nextTitle);
      upsertThread(updatedThread);
      setRenamingThreadId(null);
      setRenameValue('');
    } catch (err) {
      if (err?.status === 401 && typeof onLogout === 'function') {
        onLogout();
        return;
      }
      setError(err?.payload?.error || err?.message || 'Unable to rename this chat.');
    } finally {
      setThreadBusyId(null);
    }
  }

  async function handleDeleteThread(thread) {
    if (!window.confirm(`Delete "${thread.title}"?`)) return;

    setThreadBusyId(thread.id);
    setError('');
    try {
      await deleteThread(thread.id);
      const remainingThreads = threads.filter(existingThread => existingThread.id !== thread.id);

      if (remainingThreads.length === 0) {
        const replacementThread = await createThread();
        setThreads([replacementThread]);
        setActiveThreadId(replacementThread.id);
      } else {
        setThreads(sortThreads(remainingThreads));
        if (thread.id === activeThreadId) {
          setActiveThreadId(remainingThreads[0].id);
        }
      }
      setRenamingThreadId(null);
      setRenameValue('');
    } catch (err) {
      if (err?.status === 401 && typeof onLogout === 'function') {
        onLogout();
        return;
      }
      setError(err?.payload?.error || err?.message || 'Unable to delete this chat.');
    } finally {
      setThreadBusyId(null);
    }
  }

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || sending || !activeThreadId) return;
    if (session.limit_reached) {
      setError('You have reached the question limit for this chat. Reset the session to continue.');
      return;
    }
    const tempAssistantId = `streaming-assistant-${Date.now()}`;
    setMessages(prev => [
      ...prev,
      { role: 'user', content: trimmed },
      { id: tempAssistantId, role: 'assistant', content: '', isStreamingPlaceholder: true }
    ]);
    setInput('');
    setSending(true);
    setSendPhase('thinking');
    setStreamingReplyStarted(false);
    setError('');
    try {
      const response = await sendMessageStream(activeThreadId, trimmed, {
        onDelta(chunk) {
          setStreamingReplyStarted(true);
          setSendPhase('replying');
          setMessages(prev => prev.map(message => (
            message.id === tempAssistantId
              ? { ...message, content: `${message.content || ''}${chunk}` }
              : message
          )));
        }
      });

      const assistantMessage = response.message
        || (response.messages || []).find(entry => entry.role === 'assistant')
        || { role: 'assistant', content: '...' };
      setMessages(prev => prev.map(message => (
        message.id === tempAssistantId ? { ...message, ...assistantMessage } : message
      )));

      if (response.session) {
        setSession(prev => ({ ...prev, ...response.session }));
      }
      if (response.thread) {
        upsertThread(response.thread);
      }
    } catch (err) {
      const isAuthError = err?.status === 401;
      const fallback = isAuthError
        ? 'Your session has expired. Please log in again.'
        : err?.payload?.error || err?.message || 'Something went wrong. Please try again.';
      setMessages(prev => prev.map(message => (
        message.id === tempAssistantId ? { ...message, content: fallback } : message
      )));
      setError(fallback);
      if (isAuthError && typeof onLogout === 'function') onLogout();
    } finally {
      setSending(false);
      setSendPhase('');
      setStreamingReplyStarted(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  async function handleReset() {
    if (!activeThreadId) return;
    setError('');
    try {
      const response = await resetChat(activeThreadId);
      upsertThread(response.thread);
      setMessages([]);
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
            <button
              className={`ghost-btn ${darkMode ? 'dark' : 'light'}`}
              onClick={handleReset}
              disabled={loadingThreads || loading || sending || !activeThreadId}
            >
              Reset Session
            </button>
            <button
              className={`ghost-btn ${darkMode ? 'dark' : 'light'}`}
              onClick={onEditProfile}
              disabled={sending || typeof onEditProfile !== 'function'}
            >
              Questionnaire
            </button>
            <button className={`ghost-btn ${darkMode ? 'dark' : 'light'}`} onClick={onLogout} disabled={sending}>
              Logout
            </button>
            <div className={`user-profile ${darkMode ? 'dark' : 'light'}`}>
              <div className="user-avatar">{initials}</div>
              <div className="user-details">
                <span className={`user-name ${darkMode ? 'dark' : 'light'}`}>{displayName}</span>
                <span className="user-status">{loadingThreads || loading ? 'Syncing...' : 'Online'}</span>
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
          <ChatSidebar
            darkMode={darkMode}
            threads={threads}
            activeThreadId={activeThreadId}
            creatingThread={creatingThread}
            renamingThreadId={renamingThreadId}
            renameValue={renameValue}
            threadBusyId={threadBusyId}
            onCreateThread={handleCreateThread}
            onSelectThread={handleSelectThread}
            onStartRename={handleStartRename}
            onRenameValueChange={setRenameValue}
            onRenameSubmit={handleRenameThread}
            onRenameCancel={() => {
              setRenamingThreadId(null);
              setRenameValue('');
            }}
            onDeleteThread={handleDeleteThread}
          />

          <div className="chat-main-panel">
            <div className="chatgpt-messages">
              {!loading && messages.length === 0 && (
                <div className={`chat-empty-state ${darkMode ? 'dark' : 'light'}`}>
                  <h2>{`Hello ${welcomeName}`}</h2>
                  <p>What do you want to learn today?</p>
                </div>
              )}
              {messages.map((m, idx) => {
                const isAi = m.role === 'assistant';
                const hideEmptyStreamingPlaceholder =
                  m.isStreamingPlaceholder && typeof m.content === 'string' && m.content.trim().length === 0;

                if (hideEmptyStreamingPlaceholder) {
                  return null;
                }

                return (
                  <div
                    key={m.id || idx}
                    className={`message-row ${isAi ? 'ai' : 'user'} ${darkMode ? 'dark' : 'light'}`}
                  >
                    <div className="message-avatar">
                      {isAi ? <img src={logo} alt="Mama Akinyi" className="avatar-logo" /> : initials}
                    </div>
                    <div className="message-content">
                      <div className="message-name">{isAi ? 'Mama Akinyi' : displayName}</div>
                      <div className="message-text"><MessageBody content={m.content} /></div>
                    </div>
                  </div>
                );
              })}
              {sending && !streamingReplyStarted && (
                <div className={`message-row ai ${darkMode ? 'dark' : 'light'}`}>
                  <div className="message-avatar">
                    <img src={logo} alt="Mama Akinyi" className="avatar-logo" />
                  </div>
                  <div className="message-content">
                    <div className="message-name">Mama Akinyi</div>
                    <div className="message-text thinking">
                      <span className="thinking-label">{sendPhase === 'thinking' ? 'Thinking' : 'Replying'}</span>
                      <span className="thinking-dots" aria-hidden="true">
                        <span className="thinking-dot" />
                        <span className="thinking-dot" />
                        <span className="thinking-dot" />
                      </span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className={`chatgpt-input ${darkMode ? 'dark' : 'light'}`}>
              <div className={`input-bar ${darkMode ? 'dark' : 'light'}`}>
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder={activeThreadId ? 'Send a message...' : 'Create a chat to get started...'}
                  onKeyDown={handleKeyDown}
                  rows={1}
                  disabled={sending || !activeThreadId || session.limit_reached}
                />
                <button
                  type="button"
                  aria-label="Send"
                  onClick={handleSend}
                  disabled={sending || !input.trim() || !activeThreadId || session.limit_reached}
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
    </div>
  );
}

export default ChatWindow;
