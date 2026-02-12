import { useCallback, useEffect, useState } from 'react';
import './App.css';
import {
  login as apiLogin,
  logout as apiLogout,
  fetchSession,
  registerUser,
  resetChat,
  fetchQuestionnaire,
  saveQuestionnaire,
  fetchHistory
} from './api';
import ChatWindow from './components/ChatWindow';
import Login from './components/login';
import Questionnaire from './components/Questionnaire';
import StartCards from './components/StartCards';

function App() {
  const [user, setUser] = useState(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [view, setView] = useState('login');
  const [homeError, setHomeError] = useState('');
  const [homeWorking, setHomeWorking] = useState(false);
  const [questionnaireAnswers, setQuestionnaireAnswers] = useState(null);
  const [questionnaireError, setQuestionnaireError] = useState('');
  const [questionnaireSaving, setQuestionnaireSaving] = useState(false);
  const [justRegistered, setJustRegistered] = useState(false);
  const [pendingPrompt, setPendingPrompt] = useState('');
  const [launchTypingPractice, setLaunchTypingPractice] = useState(false);

  const loadQuestionnaire = useCallback(async () => {
    setQuestionnaireError('');
    try {
      const data = await fetchQuestionnaire();
      if (data && data.answers) {
        setQuestionnaireAnswers(data.answers);
        return { needsQuestionnaire: false, answers: data.answers };
      }
      setQuestionnaireAnswers(null);
      setView('questionnaire');
      return { needsQuestionnaire: true, answers: null };
    } catch (error) {
      if (error?.status === 404) {
        setQuestionnaireAnswers(null);
        setView('questionnaire');
        return { needsQuestionnaire: true, answers: null };
      }
      setQuestionnaireError(
        error?.payload?.error ||
          error?.payload?.message ||
          error?.message ||
          'Unable to load the questionnaire.'
      );
      return { needsQuestionnaire: false, answers: null, error: true };
    }
  }, []);

  const routeAfterAuth = useCallback(async (_user, { isRegister } = {}) => {
    const questionnaireStatus = await loadQuestionnaire();
    if (questionnaireStatus?.needsQuestionnaire) {
      return;
    }

    if (isRegister) {
      setView('chat');
      return;
    }

    try {
      const history = await fetchHistory(1);
      if (Array.isArray(history) && history.length > 0) {
        setView('home');
      } else {
        setView('chat');
      }
    } catch {
      setView('home');
    }
  }, [loadQuestionnaire]);

  useEffect(() => {
    let mounted = true;

    async function bootstrap() {
      setIsBootstrapping(true);
      try {
        const sessionUser = await fetchSession();
        if (!mounted) return;
        if (sessionUser) {
          setUser(sessionUser);
          setJustRegistered(false);
          await routeAfterAuth(sessionUser, { source: 'bootstrap', isRegister: false });
        } else {
          setUser(null);
          setView('login');
        }
      } finally {
        if (mounted) setIsBootstrapping(false);
      }
    }

    bootstrap();

    return () => {
      mounted = false;
    };
  }, [routeAfterAuth]);

  useEffect(() => {
    if (!isBootstrapping && !user) {
      setView('login');
    }
  }, [isBootstrapping, user]);

  const handleLogin = useCallback(async (username, pin) => {
    try {
      const userData = await apiLogin(username, pin);
      setUser(userData);
      setJustRegistered(false);
      await routeAfterAuth(userData, { source: 'login', isRegister: false });
      return { success: true };
    } catch (error) {
      const message =
        error?.payload?.error ||
        error?.payload?.message ||
        error?.message ||
        'Unable to log in. Please try again.';
      return { success: false, message };
    }
  }, [routeAfterAuth]);

  const handleLogout = useCallback(async () => {
    await apiLogout();
    setUser(null);
    setView('login');
    setQuestionnaireAnswers(null);
    setQuestionnaireError('');
    setJustRegistered(false);
    setPendingPrompt('');
    setLaunchTypingPractice(false);
  }, []);

  const handleRegister = useCallback(async payload => {
    try {
      const userData = await registerUser(payload);
      setUser(userData);
      setJustRegistered(true);
      await routeAfterAuth(userData, { source: 'register', isRegister: true });
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
  }, [routeAfterAuth]);

  const handleHome = useCallback(() => {
    setHomeError('');
    setView('home');
  }, []);

  const handleResumeChat = useCallback(() => {
    setHomeError('');
    setView('chat');
  }, []);

  const handleStartNewChat = useCallback(async () => {
    setHomeError('');
    setHomeWorking(true);
    try {
      await resetChat();
      setView('chat');
    } catch (error) {
      const message =
        error?.payload?.error ||
        error?.payload?.message ||
        error?.message ||
        'Unable to start a new chat.';
      setHomeError(message);
    } finally {
      setHomeWorking(false);
    }
  }, []);

  const handleStartCard = useCallback(card => {
    if (!card?.prompt) return;
    setPendingPrompt(card.prompt);
    setLaunchTypingPractice(Boolean(card.typingPractice));
    setView('chat');
  }, []);

  const handleStarterConsumed = useCallback(() => {
    setPendingPrompt('');
    setLaunchTypingPractice(false);
  }, []);

  const handleQuestionnaireSubmit = useCallback(async answers => {
    setQuestionnaireError('');
    setQuestionnaireSaving(true);
    try {
      const saved = await saveQuestionnaire(answers);
      setQuestionnaireAnswers(saved?.answers || answers);
      if (justRegistered) {
        setView('chat');
        setJustRegistered(false);
      } else {
        setView('home');
      }
    } catch (error) {
      const message =
        error?.payload?.error ||
        error?.payload?.message ||
        error?.message ||
        'Unable to save the questionnaire.';
      setQuestionnaireError(message);
    } finally {
      setQuestionnaireSaving(false);
    }
  }, [justRegistered]);

  const handleQuestionnaireEdit = useCallback(() => {
    setQuestionnaireError('');
    setView('questionnaire');
  }, []);

  if (isBootstrapping) {
    return <div className="App">Loading...</div>;
  }

  const displayName = (user?.full_name || user?.username || 'User').trim() || 'User';

  return (
    <div className="App">
      {view === 'login' || !user ? (
        <Login onLogin={handleLogin} onRegister={handleRegister} />
      ) : view === 'questionnaire' ? (
        <Questionnaire
          user={user}
          initialAnswers={questionnaireAnswers}
          onSubmit={handleQuestionnaireSubmit}
          onCancel={questionnaireAnswers ? handleHome : undefined}
          submitting={questionnaireSaving}
          error={questionnaireError}
        />
      ) : view === 'home' ? (
        <div className="home-shell">
          <div className="home-card">
            <h2>Welcome back, {displayName}</h2>
            <p className="home-subtitle">Choose a quick start or resume chat.</p>
            <StartCards
              onSelect={handleStartCard}
              title="Quick starts"
              subtitle="Tap a card"
            />
            <div className="home-actions">
              <button className="home-btn primary" onClick={handleResumeChat} disabled={homeWorking}>
                Resume chat
              </button>
              <button className="home-btn" onClick={handleStartNewChat} disabled={homeWorking}>
                {homeWorking ? 'Starting...' : 'Start new chat'}
              </button>
            </div>
            {questionnaireAnswers && (
              <button type="button" className="link-button" onClick={handleQuestionnaireEdit}>
                Review or edit onboarding questionnaire
              </button>
            )}
            {questionnaireAnswers && <p className="home-success">Onboarding complete ✅</p>}
            {homeError && <p className="home-error">{homeError}</p>}
            {questionnaireError && <p className="home-error">{questionnaireError}</p>}
          </div>
        </div>
      ) : (
        <ChatWindow
          user={user}
          onLogout={handleLogout}
          onHome={handleHome}
          pendingPrompt={pendingPrompt}
          launchTypingPractice={launchTypingPractice}
          onStarterConsumed={handleStarterConsumed}
        />
      )}
    </div>
  );
}

export default App;
