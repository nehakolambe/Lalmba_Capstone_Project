// CRA proxy (package.json) forwards API calls to the Flask backend.
const API_BASE = '';

function buildUrl(path) {
  if (!path) return '/';
  return path.startsWith('/') ? path : `/${path}`;
}

async function request(path, { method = 'GET', body, headers = {} } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${buildUrl(path)}`, {
      method,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...headers
      },
      body: body ? JSON.stringify(body) : undefined
    });
  } catch (networkError) {
    // TIP: "Cannot connect to server" usually means the Flask API isn't running
    // or the CRA proxy target is unavailable.
    const error = new Error('Cannot connect to server');
    error.cause = networkError;
    error.network = true;
    throw error;
  }

  let data = null;
  if (response.status !== 204) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
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
  } catch {
    return null;
  }
}

export async function login(username, pin) {
  const data = await request('/auth/login', { method: 'POST', body: { username, pin } });
  return data.user;
}

export async function logout() {
  try {
    await request('/auth/logout', { method: 'POST' });
  } catch {
    // Ignore network errors on logout.
  }
}

export async function registerUser({ fullName, username, pin, details }) {
  const data = await request('/auth/register', {
    method: 'POST',
    body: { fullName, username, pin, details }
  });
  return data.user;
}

export async function fetchHistory(limit = 50) {
  const data = await request(`/chat/history?limit=${limit}`);
  return data.history || [];
}

export async function sendMessage(text) {
  const data = await request('/chat/message', {
    method: 'POST',
    body: { text }
  });
  return {
    messages: data.messages || [],
    sources: data.sources || []
  };
}

export async function resetChat() {
  await request('/chat/reset', { method: 'POST' });
}

export async function fetchProgress() {
  const data = await request('/progress');
  const items = data.progress || [];
  const current = Number.isFinite(data.current) ? data.current : items.length;
  const max = Number.isFinite(data.max) ? data.max : 10;
  return { items, current, max };
}

export async function recordProgress(milestone, notes = '') {
  const data = await request('/progress', {
    method: 'POST',
    body: { milestone, notes }
  });
  return data.progress;
}

export async function incrementProgress() {
  const data = await request('/progress/increment', { method: 'POST' });
  const current = Number.isFinite(data.current) ? data.current : 0;
  const max = Number.isFinite(data.max) ? data.max : 10;
  return { current, max, capped: Boolean(data.capped) };
}

export async function fetchQuestionnaire() {
  const data = await request('/questionnaire/me');
  return data.questionnaire || null;
}

export async function saveQuestionnaire(answers) {
  const data = await request('/questionnaire/me', {
    method: 'POST',
    body: { answers }
  });
  return data.questionnaire || null;
}
