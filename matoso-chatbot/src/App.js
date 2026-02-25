import React, { useState, useEffect } from "react";
import LandingPage from "./components/LandingPage";
import Login from "./components/Login";
import ChatWindow from "./components/ChatWindow";
import { fetchSession, login, registerUser } from "./api";
import "./App.css";

function App() {
  const [page, setPage] = useState("landing");
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetchSession().then((sessionUser) => {
      if (sessionUser) {
        setUser(sessionUser);
        setPage("chat");
      }
    });
  }, []);

  async function handleLogin(username, pin) {
    try {
      const sessionUser = await login(username, pin);
      setUser(sessionUser);
      setPage("chat");
      return { success: true };
    } catch (err) {
      return {
        success: false,
        message: err.message || "Login failed. Please try again.",
      };
    }
  }

  async function handleRegister({ fullName, username, pin, details }) {
    try {
      const sessionUser = await registerUser({ fullName, username, pin, details });
      setUser(sessionUser);
      setPage("chat");
      return { success: true };
    } catch (err) {
      return {
        success: false,
        message: err.message || "Registration failed. Please try again.",
      };
    }
  }

  return (
    <div>
      {page === "landing" && (
        <LandingPage
          onLogin={() => setPage("login")}
          onSignup={() => setPage("signup")}
        />
      )}

      {page === 'login' && (
        <Login
          initialMode="login"
          onLogin={handleLogin}
          onRegister={handleRegister}
          onBack={() => setPage('landing')}
        />
      )}

      {page === 'signup' && (
        <Login
          initialMode="register"
          onLogin={handleLogin}
          onRegister={handleRegister}
          onBack={() => setPage('landing')}
        />
      )}

      {page === "chat" && (
        <ChatWindow
          user={user}
          onLogout={() => {
            setUser(null);
            setPage("landing");
          }}
        />
      )}
    </div>
  );
}

export default App;