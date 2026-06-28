import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './components/HomePage';
import { useStore } from './store/useStore';
import './style.css';

// Public Pages
import About from './pages/About';
import Features from './pages/Features';
import Contact from './pages/Contact';

// User Pages
import Login from './pages/USER/Login';
import Register from './pages/USER/Register';
// EMAIL VERIFICATION DISABLED
// import VerifyEmail from './pages/USER/VerifyEmail';
import ForgotPassword from './pages/USER/ForgotPassword';
import ResetPassword from './pages/USER/ResetPassword';
import UserDashboard from './pages/USER/Dashboard';
import Quizzes from './pages/USER/Quizzes';
import QuizAttempt from './pages/USER/QuizAttempt';
import QuizResults from './pages/USER/QuizResults';
import AIQuiz from './pages/USER/AIQuiz';
import Profile from './pages/USER/Profile';
import Settings from './pages/USER/Settings';
import InterestAssessment from './pages/USER/InterestAssessment';
import RecentQuizzes from './pages/USER/RecentQuizzes';
import Chat from './pages/USER/Chat';
import Feedback from './pages/USER/Feedback';
import LearningPath from './pages/USER/LearningPath';
import RemediationLesson from './pages/USER/RemediationLesson';
import Notes from './pages/USER/Notes';

// Admin Pages
import AdminLogin from './pages/ADMIN/AdminLogin';
import Dashboard from './pages/ADMIN/Dashboard';
import Users from './pages/ADMIN/Users';
import Analytics from './pages/ADMIN/Analytics';
import Reports from './pages/ADMIN/Reports';
import Logs from './pages/ADMIN/Logs';
import AdminFeedback from './pages/ADMIN/Feedback';
import AdminSettings from './pages/ADMIN/Settings';
import AdminCatalog from './pages/ADMIN/AdminCatalog';
import AdminLayout from './components/Admin/AdminLayout';
import ProtectedAdminRoute from './components/Admin/ProtectedAdminRoute';
import ProtectedInterestRoute from './components/ProtectedInterestRoute';


const App: React.FC = () => {
  const { initializeAuth, theme, setTheme } = useStore();

  useEffect(() => {
    // Initialize auth state
    const initAuth = async () => {
      await initializeAuth();
    };
    initAuth();
  }, [initializeAuth]);

  useEffect(() => {
    // Initialize theme on mount
    setTheme(theme);

    // Listen for system theme changes if theme is set to 'auto'
    if (theme === 'auto') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => {
        setTheme('auto');
      };
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [theme, setTheme]);

  return (
    <Router>
      <Routes>
        {/* Public Layout Route with Navbar and Footer */}
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />

          {/* Public Pages */}
          <Route path="/about" element={<About />} />
          <Route path="/features" element={<Features />} />
          <Route path="/contact" element={<Contact />} />

          {/* User Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          {/* EMAIL VERIFICATION DISABLED */}
          {/* <Route path="/verify-email" element={<VerifyEmail />} /> */}
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/dashboard" element={<UserDashboard />} />
          <Route path="/quizzes" element={<Quizzes />} />
          <Route path="/quizzes/recent" element={<RecentQuizzes />} />
          <Route path="/ai-quiz" element={<AIQuiz />} />
          <Route path="/quiz/:quizId" element={<QuizAttempt />} />
          <Route path="/quiz/results/:attemptId" element={<QuizResults />} />
          <Route path="/remediation/:attemptId" element={<RemediationLesson />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/feedback" element={<Feedback />} />
          <Route path="/learning-path" element={<LearningPath />} />
          <Route path="/recommendations" element={<Navigate to="/learning-path" replace />} />
          <Route path="/notes" element={<Notes />} />

          {/* Protected Interest Assessment Route - requires login (canonical path under /quizzes) */}
          <Route element={<ProtectedInterestRoute />}>
            <Route path="/interest-check" element={<Navigate to="/quizzes/interest-check" replace />} />
            <Route path="/quizzes/interest-check" element={<InterestAssessment />} />
          </Route>
        </Route>

        {/* Admin Auth */}
        <Route path="/admin/login" element={<AdminLogin />} />

        {/* Admin Protected Area */}
        <Route element={<ProtectedAdminRoute />}>
          <Route element={<AdminLayout />}>
            <Route path="/admin" element={<Dashboard />} />
            <Route path="/admin/users" element={<Users />} />
            <Route path="/admin/catalog" element={<AdminCatalog />} />
            <Route path="/admin/content" element={<Navigate to="/admin/catalog" replace />} />
            <Route path="/admin/learning-paths" element={<Navigate to="/admin/catalog" replace />} />
            <Route path="/admin/analytics" element={<Analytics />} />
            <Route path="/admin/reports" element={<Reports />} />
            <Route path="/admin/logs" element={<Logs />} />
            <Route path="/admin/feedback" element={<AdminFeedback />} />
            <Route path="/admin/settings" element={<AdminSettings />} />
          </Route>
        </Route>

        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
};

export default App;
