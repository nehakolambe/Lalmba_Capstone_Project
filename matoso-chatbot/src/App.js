import React, { useState, useEffect } from "react";
import LandingPage from "./components/LandingPage";
import Login from "./components/Login";
import ChatWindow from "./components/ChatWindow";
import Questionnaire from "./components/Questionnaire";
import { fetchProfile, fetchSession, login, registerUser, updateProfile } from "./api";
import "./App.css";

function App() {
  const [page, setPage] = useState("landing");
  const [user, setUser] = useState(null);
  const [questionnaireMode, setQuestionnaireMode] = useState("onboarding");

  useEffect(() => {
    fetchSession().then((sessionUser) => {
      if (sessionUser) {
        setUser(sessionUser);
        setPage(sessionUser.profile_complete ? "chat" : "questionnaire");
      }
    });
  }, []);

  async function handleLogin(username, pin) {
    try {
      const sessionUser = await login(username, pin);
      setUser(sessionUser);
      setQuestionnaireMode("onboarding");
      setPage(sessionUser.profile_complete ? "chat" : "questionnaire");
      return { success: true };
    } catch (err) {
      return {
        success: false,
        message: err.message || "Login failed. Please try again.",
      };
    }
  }

  async function handleRegister({ fullName, username, pin }) {
    try {
      const sessionUser = await registerUser({ fullName, username, pin });
      setUser(sessionUser);
      setQuestionnaireMode("onboarding");
      setPage(sessionUser.profile_complete ? "chat" : "questionnaire");
      return { success: true };
    } catch (err) {
      return {
        success: false,
        message: err.message || "Registration failed. Please try again.",
      };
    }
  }

  async function handleSaveProfile(profile) {
    const updatedUser = await updateProfile(profile);
    setUser(updatedUser);
    setPage("chat");
    setQuestionnaireMode("edit");
    return updatedUser;
  }

  async function handleOpenQuestionnaire() {
    if (!user) return;
    try {
      const profile = await fetchProfile();
      if (profile) {
        setUser(profile);
      }
    } catch {}
    setQuestionnaireMode("edit");
    setPage("questionnaire");
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
          onEditProfile={handleOpenQuestionnaire}
          onLogout={() => {
            setUser(null);
            setPage("landing");
          }}
        />
      )}

      {page === "questionnaire" && (
        <Questionnaire
          user={user}
          initialProfile={user}
          isEditing={questionnaireMode === "edit"}
          onSave={handleSaveProfile}
          onBack={questionnaireMode === "edit" ? () => setPage("chat") : undefined}
        />
      )}
    </div>
  );
}

export default App;
