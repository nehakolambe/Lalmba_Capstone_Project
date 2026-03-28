function resolveApiBase() {
  if (process.env.REACT_APP_API_BASE) {
    return process.env.REACT_APP_API_BASE;
  }

  if (typeof window !== 'undefined' && window.location.port === '3000') {
    return 'http://localhost:5000';
  }

  return '';
}

const API_BASE = resolveApiBase();

async function request(path, { method = 'GET', body, headers = {} } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: body ? JSON.stringify(body) : undefined
    });
  } catch (networkError) {
    const error = new Error('Cannot connect to server');
    error.cause = networkError;
    error.network = true;
    throw error;
  }

  let data = null;
  if (response.status !== 204) {
    try { data = await response.json(); } catch { data = null; }
  }

  if (!response.ok) {
    const message = (data && (data.error || data.message)) || response.statusText;
    const error = new Error(message || 'Request failed');
    error.status = response.status;
    error.payload = data;
    throw error;
  }

  return data;
}

async function parseJsonResponse(response) {
  let data = null;
  if (response.status !== 204) {
    try { data = await response.json(); } catch { data = null; }
  }

  if (!response.ok) {
    const message = (data && (data.error || data.message)) || response.statusText;
    const error = new Error(message || 'Request failed');
    error.status = response.status;
    error.payload = data;
    throw error;
  }

  return data;
}

export async function fetchSession() {
  try {
    const data = await request('/auth/me');
    return data.user || null;
  } catch { return null; }
}

export async function login(username, pin) {
  const data = await request('/auth/login', { method: 'POST', body: { username, pin } });
  return data.user;
}

export async function logout() {
  try { await request('/auth/logout', { method: 'POST' }); } catch {}
}

export async function registerUser({ fullName, username, pin }) {
  const data = await request('/auth/register', {
    method: 'POST',
    body: { fullName, username, pin }
  });
  return data.user;
}

export async function fetchProfile() {
  const data = await request('/auth/profile');
  return data.profile || data.user || null;
}

export async function updateProfile(profile) {
  const data = await request('/auth/profile', {
    method: 'PATCH',
    body: profile
  });
  return data.user || data.profile;
}

export async function fetchThreads() {
  const data = await request('/chat/threads');
  return data.threads || [];
}

export async function createThread(title = '') {
  const data = await request('/chat/threads', {
    method: 'POST',
    body: title ? { title } : {}
  });
  return data.thread;
}

export async function renameThread(threadId, title) {
  const data = await request(`/chat/threads/${threadId}`, {
    method: 'PATCH',
    body: { title }
  });
  return data.thread;
}

export async function deleteThread(threadId) {
  await request(`/chat/threads/${threadId}`, { method: 'DELETE' });
}

export async function fetchHistory(threadId, limit = 50) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (threadId != null) params.set('thread_id', String(threadId));
  return await request(`/chat/history?${params.toString()}`);
}

export async function sendMessage(threadId, text) {
  return await request('/chat/message', {
    method: 'POST',
    body: { thread_id: threadId, text }
  });
}

export async function sendMessageStream(threadId, text, handlers = {}) {
  const { onDelta, onDone, onError } = handlers;

  let response;
  try {
    response = await fetch(`${API_BASE}/chat/message/stream`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ thread_id: threadId, text })
    });
  } catch (networkError) {
    const error = new Error('Cannot connect to server');
    error.cause = networkError;
    error.network = true;
    if (typeof onError === 'function') onError(error);
    throw error;
  }

  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/x-ndjson')) {
    const data = await parseJsonResponse(response);
    if (typeof onDone === 'function') onDone(data);
    return data;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    const error = new Error('Streaming is not supported by this browser');
    if (typeof onError === 'function') onError(error);
    throw error;
  }

  const decoder = new TextDecoder();
  let buffer = '';
  let donePayload = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      let event;
      try {
        event = JSON.parse(trimmed);
      } catch {
        continue;
      }

      if (event.type === 'delta') {
        if (typeof onDelta === 'function') onDelta(event.content || '');
      } else if (event.type === 'done') {
        donePayload = event;
        if (typeof onDone === 'function') onDone(event);
      } else if (event.type === 'error') {
        const error = new Error(event.error || 'Streaming request failed');
        error.payload = event;
        if (typeof onError === 'function') onError(error);
        throw error;
      }
    }
  }

  if (buffer.trim()) {
    try {
      const event = JSON.parse(buffer.trim());
      if (event.type === 'done') {
        donePayload = event;
        if (typeof onDone === 'function') onDone(event);
      } else if (event.type === 'error') {
        const error = new Error(event.error || 'Streaming request failed');
        error.payload = event;
        if (typeof onError === 'function') onError(error);
        throw error;
      }
    } catch {}
  }

  if (!donePayload) {
    const error = new Error('Streaming response ended unexpectedly');
    if (typeof onError === 'function') onError(error);
    throw error;
  }

  return donePayload;
}

export async function resetChat(threadId) {
  return await request('/chat/reset', {
    method: 'POST',
    body: { thread_id: threadId }
  });
}

export async function fetchProgress(threadId) {
  const suffix = threadId != null ? `?thread_id=${encodeURIComponent(threadId)}` : '';
  const data = await request(`/progress${suffix}`);
  return data.progress || [];
}

export async function recordProgress(threadId, milestone, notes = '') {
  const data = await request('/progress', {
    method: 'POST',
    body: { thread_id: threadId, milestone, notes }
  });
  return data.progress;
}

export async function resetProgress(threadId) {
  await request('/progress/reset', {
    method: 'POST',
    body: { thread_id: threadId }
  });
}
