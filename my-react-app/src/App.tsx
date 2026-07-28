import React, { useEffect, lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './components/HomePage';
import { useStore } from './store/useStore';
import './style.css';

// Public Pages — lazy loaded
const About = lazy(() => import('./pages/About'));
const Features = lazy(() => import('./pages/Features'));
const Contact = lazy(() => import('./pages/Contact'));

// User Pages — lazy loaded
const Login = lazy(() => import('./pages/USER/Login'));
const Register = lazy(() => import('./pages/USER/Register'));
const VerifyEmail = lazy(() => import('./pages/USER/VerifyEmail'));
const ForgotPassword = lazy(() => import('./pages/USER/ForgotPassword'));
const ResetPassword = lazy(() => import('./pages/USER/ResetPassword'));
const UserDashboard = lazy(() => import('./pages/USER/Dashboard'));
const Quizzes = lazy(() => import('./pages/USER/Quizzes'));
const QuizAttempt = lazy(() => import('./pages/USER/QuizAttempt'));
const QuizResults = lazy(() => import('./pages/USER/QuizResults'));
const AIQuiz = lazy(() => import('./pages/USER/AIQuiz'));
const Profile = lazy(() => import('./pages/USER/Profile'));
const Settings = lazy(() => import('./pages/USER/Settings'));
const InterestAssessment = lazy(() => import('./pages/USER/InterestAssessment'));
const RecentQuizzes = lazy(() => import('./pages/USER/RecentQuizzes'));
const Chat = lazy(() => import('./pages/USER/Chat'));
const Feedback = lazy(() => import('./pages/USER/Feedback'));
const LearningPath = lazy(() => import('./pages/USER/LearningPath'));
const RemediationLesson = lazy(() => import('./pages/USER/RemediationLesson'));
const Notes = lazy(() => import('./pages/USER/Notes'));

// Admin Pages — lazy loaded
const AdminLogin = lazy(() => import('./pages/ADMIN/AdminLogin'));
const Dashboard = lazy(() => import('./pages/ADMIN/Dashboard'));
const Users = lazy(() => import('./pages/ADMIN/Users'));
const Analytics = lazy(() => import('./pages/ADMIN/Analytics'));
const Reports = lazy(() => import('./pages/ADMIN/Reports'));
const Logs = lazy(() => import('./pages/ADMIN/Logs'));
const AdminFeedback = lazy(() => import('./pages/ADMIN/Feedback'));
const AdminSettings = lazy(() => import('./pages/ADMIN/Settings'));
const AdminCatalog = lazy(() => import('./pages/ADMIN/AdminCatalog'));
import AdminLayout from './components/Admin/AdminLayout';
import ProtectedAdminRoute from './components/Admin/ProtectedAdminRoute';
import ProtectedInterestRoute from './components/ProtectedInterestRoute';

// Minimal full-page spinner shown while lazy chunks load
const PageLoader: React.FC = () => (
  <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 transition-colors duration-300">
    <div className="flex flex-col items-center gap-4">
      <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      <p className="text-sm text-slate-500">Loading…</p>
    </div>
  </div>
);

const CatchAllRedirect: React.FC = () => {
  const { isAuthenticated } = useStore();
  return <Navigate to={isAuthenticated ? '/home' : '/'} replace />;
};

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
      <Suspense fallback={<PageLoader />}>
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
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/home" element={<UserDashboard />} />
            <Route path="/dashboard" element={<Navigate to="/home" replace />} />
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
          <Route path="*" element={<CatchAllRedirect />} />
        </Routes>
      </Suspense>
    </Router>
  );
};

export default App;

