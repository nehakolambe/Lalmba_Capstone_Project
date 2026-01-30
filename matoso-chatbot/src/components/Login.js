import React, { useState } from 'react';

function Login({ onLogin, onRegister }) {
  const [username, setUsername] = useState('');
  const [pin, setPin] = useState('');
  const [fullName, setFullName] = useState('');
  const [details, setDetails] = useState('');
  const [mode, setMode] = useState('login');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');

  function surfaceError(message = '', details) {
    const detailText =
      details && typeof details === 'object'
        ? Object.values(details)
            .filter(Boolean)
            .join(' ')
        : typeof details === 'string'
        ? details
        : '';
    const combined = [message, detailText].filter(Boolean).join(' ');
    setError(combined || 'Unexpected error. Please try again.');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting) return;

    setSubmitting(true);
    setError('');
    setFeedback('');

    try {
      if (mode === 'login') {
        const result = await onLogin(username, pin);
        if (!result || !result.success) {
          surfaceError(result?.message || 'Unable to log in. Please try again.', result?.details);
        } else {
          setPin('');
        }
      } else {
        if (typeof onRegister !== 'function') {
          surfaceError('Registration is currently unavailable.');
          return;
        }

        const result = await onRegister({
          fullName,
          username,
          pin,
          details
        });

        if (!result || !result.success) {
          surfaceError(result?.message || 'Unable to register. Please try again.', result?.details);
        } else {
          setFeedback('Account created! Logging you in...');
          setPin('');
          setFullName('');
          setDetails('');
        }
      }
    } catch (err) {
      // TIP: A "Cannot connect to server" message usually means the Flask backend isn't reachable or CORS blocked the call.
      surfaceError(err.message || 'Unexpected error. Please try again.', err.details);
    } finally {
      setSubmitting(false);
    }
  }

  function toggleMode() {
    setMode(prev => (prev === 'login' ? 'register' : 'login'));
    setError('');
    setFeedback('');
  }

  return (
    <form onSubmit={handleSubmit} className="login-form">
      <h2>{mode === 'login' ? 'Welcome to Matoso Help Desk' : 'Create your Matoso account'}</h2>

      {mode === 'register' && (
        <label>
          Full name:
          <input
            value={fullName}
            onChange={e => setFullName(e.target.value)}
            required
            disabled={submitting}
          />
        </label>
      )}

      <label>
        Username:
        <input
          value={username}
          onChange={e => setUsername(e.target.value)}
          required
          disabled={submitting}
        />
      </label>

      <label>
        {mode === 'login' ? 'PIN:' : 'Choose a PIN/password:'}
        <input
          type="password"
          value={pin}
          onChange={e => setPin(e.target.value)}
          required
          disabled={submitting}
          minLength={mode === 'register' ? 4 : undefined}
        />
      </label>

      {mode === 'register' && (
        <label>
          Additional details:
          <textarea
            value={details}
            onChange={e => setDetails(e.target.value)}
            disabled={submitting}
            rows={3}
            placeholder="Share anything that helps us support you."
          />
        </label>
      )}

      {error && <p className="login-error">{error}</p>}
      {feedback && <p className="login-feedback">{feedback}</p>}

      <button type="submit" disabled={submitting}>
        {submitting ? 'Please wait...' : mode === 'login' ? 'Login' : 'Create account'}
      </button>

      <p className="login-hint">
        {mode === 'login' ? 'Need an account?' : 'Already registered?'}
        <button type="button" className="link-button" onClick={toggleMode} disabled={submitting}>
          {mode === 'login' ? 'Create one here' : 'Back to login'}
        </button>
      </p>
    </form>
  );
}

export default Login;
