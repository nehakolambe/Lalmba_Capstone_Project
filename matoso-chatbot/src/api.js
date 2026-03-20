const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000';

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

export async function registerUser({ fullName, username, pin, details }) {
  const data = await request('/auth/register', {
    method: 'POST',
    body: { fullName, username, pin, details }
  });
  return data.user;
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