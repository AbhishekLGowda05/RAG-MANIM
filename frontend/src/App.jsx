import { useState } from 'react';
import { ProfileProvider, useProfile } from './context/ProfileContext';
import { SessionProvider, useSession } from './context/SessionContext';
import { ThemeProvider } from './context/ThemeContext';

// Import Screens
import Analytics from './screens/Analytics';
import Dashboard from './screens/Dashboard';
import Health from './screens/Health';
import KnowledgeGraph from './screens/KnowledgeGraph';
import Landing from './screens/Landing';
import Library from './screens/Library';
import Onboarding from './screens/Onboarding';
import Profile from './screens/Profile';
import ScriptInspector from './screens/ScriptInspector';
import Workspace from './screens/Workspace';

// Import Common Components
import Sidebar from './components/Sidebar';

function AppContent() {
  const { profile, loading } = useProfile();
  const { resetProfile } = useProfile();
  
  // Navigation states
  const [showLanding, setShowLanding] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingInitialStep, setOnboardingInitialStep] = useState(1);
  const [activeScreen, setActiveScreen] = useState('dashboard');
  const [pendingTopic, setPendingTopic] = useState(null);
  const { startPipeline } = useSession();

  if (loading) {
    return (
      <div
        style={{
          width: '100vw',
          height: '100vh',
          background: 'var(--bg-base)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          color: 'var(--text-primary)',
          fontSize: '18px',
          fontFamily: 'var(--font-ui)',
          letterSpacing: '0.05em'
        }}
      >
        <div className="generating" style={{ padding: 'var(--space-6) var(--space-10)', borderRadius: 'var(--r-md)' }}>
          Bootstrapping LearnOS Terminal...
        </div>
      </div>
    );
  }

  // S-01 Cinematic Landing page view
  if (showLanding) {
    return (
      <Landing
        onStart={(topic) => {
          setShowLanding(false);
          // If a spoken/written topic is provided, attempt to start pipeline (after onboarding if needed)
          if (topic && topic.trim().length > 0) {
            if (!profile.name || profile.name.trim() === '') {
              // Save pending topic and route to onboarding first
              setPendingTopic(topic);
              setShowOnboarding(true);
            } else {
              // Start pipeline immediately and open workspace
              startPipeline(topic);
              setActiveScreen('workspace');
            }
            return;
          }

          // No topic provided — route based on profile presence
          if (!profile.name || profile.name.trim() === '') {
            setShowOnboarding(true);
          } else {
            setActiveScreen('dashboard');
          }
        }}
      />
    );
  }

  // S-02 Conversational Onboarding profiling view
  if (showOnboarding) {
    return (
      <Onboarding
        initialStep={onboardingInitialStep}
        onComplete={() => {
          setShowOnboarding(false);
          setOnboardingInitialStep(1);
          // If onboarding completed and there is a pending topic (voice input), start the pipeline
          if (pendingTopic) {
            startPipeline(pendingTopic);
            setPendingTopic(null);
            setActiveScreen('workspace');
          } else {
            setActiveScreen('dashboard');
          }
        }}
      />
    );
  }

  const handleRetakeDiagnostic = () => {
    setShowLanding(false);
    setOnboardingInitialStep(5);
    setShowOnboarding(true);
  };

  // Helper function to render active dashboard widget screen
  const renderScreen = () => {
    switch (activeScreen) {
      case 'dashboard':
        return (
          <Dashboard
            setActiveScreen={setActiveScreen}
            onRetakeDiagnostic={handleRetakeDiagnostic}
          />
        );
      case 'workspace':
        return <Workspace />;
      case 'library':
        return <Library setActiveScreen={setActiveScreen} />;
      case 'graph':
        return <KnowledgeGraph setActiveScreen={setActiveScreen} />;
      case 'analytics':
        return <Analytics />;
      case 'inspector':
        return <ScriptInspector />;
      case 'profile':
        return <Profile />;
      case 'health':
        return <Health />;
      default:
        return <Dashboard setActiveScreen={setActiveScreen} />;
    }
  };

  const handleSignOut = async () => {
    try {
      await resetProfile();
    } catch (e) {
      console.warn('Sign out: failed to reset profile locally', e);
    }
    // Route user to onboarding after signing out
    setShowLanding(false);
    setShowOnboarding(true);
    setActiveScreen('dashboard');
  };

  return (
    <div className="learnos-layout">
      {/* Persistent global Navigation drawer sidebar */}
      <Sidebar activeScreen={activeScreen} setActiveScreen={setActiveScreen} onSignOut={handleSignOut} />

      {/* Primary layout content canvas viewport */}
      <div style={{ flex: 1, height: '100%', overflow: 'hidden', position: 'relative', display: 'flex', flexDirection: 'column' }}>
        {renderScreen()}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <ProfileProvider>
        <SessionProvider>
          <AppContent />
        </SessionProvider>
      </ProfileProvider>
    </ThemeProvider>
  );
}
