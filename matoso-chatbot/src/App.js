import { useCallback, useEffect, useState } from 'react';
import './App.css';
import { login as apiLogin, logout as apiLogout, fetchSession, registerUser } from './api';
import ChatWindow from './components/ChatWindow';
import Login from './components/Login';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    fetchSession()
      .then(sessionUser => {
        if (mounted) {
          setUser(sessionUser);
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const handleLogin = useCallback(async (username, pin) => {
    try {
      const userData = await apiLogin(username, pin);
      setUser(userData);
      return { success: true };
    } catch (error) {
      const message =
        error?.payload?.error ||
        error?.payload?.message ||
        error?.message ||
        'Unable to log in. Please try again.';
      return { success: false, message };
    }
  }, []);

  const handleLogout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const handleRegister = useCallback(async payload => {
    try {
      const userData = await registerUser(payload);
      setUser(userData);
      return { success: true };
    } catch (error) {
      const details = error?.payload?.details;
      const message =
        error?.payload?.error ||
        error?.payload?.message ||
        error?.message ||
        'Unable to register. Please try again.';
      return {
        success: false,
        message,
        details
      };
    }
  }, []);

  if (loading) {
    return <div className="App">Loading...</div>;
  }

  return (
    <div className="App">
      {!user ? (
        <Login onLogin={handleLogin} onRegister={handleRegister} />
      ) : (
        <ChatWindow user={user} onLogout={handleLogout} />
      )}
    </div>
  );
}

export default App;
