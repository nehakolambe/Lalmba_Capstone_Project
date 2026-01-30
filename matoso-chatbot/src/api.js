// Keep this in sync with the Flask server host/port to avoid "Failed to fetch" errors.
const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000';

async function request(path, { method = 'GET', body, headers = {} } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
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
    // on API_BASE or the origin is missing from Config.CORS_ORIGINS.
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
  return data.messages || [];
}

export async function resetChat() {
  await request('/chat/reset', { method: 'POST' });
}

export async function fetchProgress() {
  const data = await request('/progress');
  return data.progress || [];
}

export async function recordProgress(milestone, notes = '') {
  const data = await request('/progress', {
    method: 'POST',
    body: { milestone, notes }
  });
  return data.progress;
}
