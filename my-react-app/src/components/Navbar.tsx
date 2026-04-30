import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useStore } from '../store/useStore';

const Navbar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useStore();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setIsProfileOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      navigate('/');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setIsLoggingOut(false);
    }
  };

  const getUserDisplayName = () => {
    if (user?.firstName && user?.lastName) {
      return `${user.firstName} ${user.lastName}`;
    }
    if (user?.firstName) {
      return user.firstName;
    }
    return user?.email?.split('@')[0] || 'User';
  };

  const getUserInitials = () => {
    if (user?.firstName && user?.lastName) {
      return `${user.firstName.charAt(0)}${user.lastName.charAt(0)}`.toUpperCase();
    }
    if (user?.firstName) {
      return user.firstName.charAt(0).toUpperCase();
    }
    return user?.email?.charAt(0).toUpperCase() || 'U';
  };

  return (
    <nav className="fixed top-0 left-0 right-0 w-full bg-white/95 backdrop-blur-md border-b border-gray-200 z-50 shadow-sm transition-all duration-300 hover:shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left Section: Logo and Navigation Links */}
          <div className="flex items-center gap-8">
            {/* Logo */}
            <Link to="/" className="group flex items-center space-x-2 transition-all duration-200" aria-label="PLPG Home">
              <div className="w-8 h-8 bg-indigo-600 rounded flex items-center justify-center transform group-hover:scale-110 group-hover:rotate-3 transition-all duration-300 shadow-sm group-hover:shadow-md" role="img" aria-label="PLPG Logo">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <span className="text-xl font-semibold text-gray-900 hidden sm:block group-hover:text-indigo-600 transition-colors duration-200">
                PLPG
              </span>
            </Link>

            {/* Desktop Navigation Links */}
            <div className="hidden lg:flex items-center space-x-8">
              <Link
                to="/"
                className={`relative text-sm font-medium transition-colors duration-200 ${location.pathname === '/'
                    ? 'text-indigo-600'
                    : 'text-gray-700 hover:text-indigo-600'
                  } after:absolute after:bottom-0 after:left-0 after:h-0.5 after:bg-indigo-600 after:transition-all after:duration-300 ${location.pathname === '/' ? 'after:w-full' : 'after:w-0 hover:after:w-full'}`}
              >
                Home
              </Link>
              <Link
                to="/features"
                className={`relative text-sm font-medium transition-colors duration-200 ${location.pathname === '/features'
                    ? 'text-indigo-600'
                    : 'text-gray-700 hover:text-indigo-600'
                  } after:absolute after:bottom-0 after:left-0 after:h-0.5 after:bg-indigo-600 after:transition-all after:duration-300 ${location.pathname === '/features' ? 'after:w-full' : 'after:w-0 hover:after:w-full'}`}
              >
                Features
              </Link>
              <Link
                to="/about"
                className={`relative text-sm font-medium transition-colors duration-200 ${location.pathname === '/about'
                    ? 'text-indigo-600'
                    : 'text-gray-700 hover:text-indigo-600'
                  } after:absolute after:bottom-0 after:left-0 after:h-0.5 after:bg-indigo-600 after:transition-all after:duration-300 ${location.pathname === '/about' ? 'after:w-full' : 'after:w-0 hover:after:w-full'}`}
              >
                About
              </Link>
              <Link
                to="/contact"
                className={`relative text-sm font-medium transition-colors duration-200 ${location.pathname === '/contact'
                    ? 'text-indigo-600'
                    : 'text-gray-700 hover:text-indigo-600'
                  } after:absolute after:bottom-0 after:left-0 after:h-0.5 after:bg-indigo-600 after:transition-all after:duration-300 ${location.pathname === '/contact' ? 'after:w-full' : 'after:w-0 hover:after:w-full'}`}
              >
                Contact
              </Link>
              <Link
                to="/interest-check"
                className={`relative text-sm font-medium transition-colors duration-200 ${location.pathname === '/interest-check'
                    ? 'text-indigo-600'
                    : 'text-gray-700 hover:text-indigo-600'
                  } after:absolute after:bottom-0 after:left-0 after:h-0.5 after:bg-indigo-600 after:transition-all after:duration-300 ${location.pathname === '/interest-check' ? 'after:w-full' : 'after:w-0 hover:after:w-full'}`}
              >
                Interest Check
              </Link>
              {isAuthenticated && (
                <>
                  <Link
                    to="/quizzes"
                    className={`relative text-sm font-medium transition-colors duration-200 ${location.pathname === '/quizzes'
                        ? 'text-indigo-600'
                        : 'text-gray-700 hover:text-indigo-600'
                      } after:absolute after:bottom-0 after:left-0 after:h-0.5 after:bg-indigo-600 after:transition-all after:duration-300 ${location.pathname === '/quizzes' ? 'after:w-full' : 'after:w-0 hover:after:w-full'}`}
                  >
                    Quizzes
                  </Link>
                  <Link
                    to="/learning-path"
                    className={`relative text-sm font-medium transition-colors duration-200 ${location.pathname === '/learning-path'
                        ? 'text-indigo-600'
                        : 'text-gray-700 hover:text-indigo-600'
                      } after:absolute after:bottom-0 after:left-0 after:h-0.5 after:bg-indigo-600 after:transition-all after:duration-300 ${location.pathname === '/learning-path' ? 'after:w-full' : 'after:w-0 hover:after:w-full'}`}
                  >
                    My Path
                  </Link>
                  <Link
                    to="/notes"
                    className={`relative text-sm font-medium transition-colors duration-200 ${location.pathname === '/notes'
                        ? 'text-indigo-600'
                        : 'text-gray-700 hover:text-indigo-600'
                      } after:absolute after:bottom-0 after:left-0 after:h-0.5 after:bg-indigo-600 after:transition-all after:duration-300 ${location.pathname === '/notes' ? 'after:w-full' : 'after:w-0 hover:after:w-full'}`}
                  >
                    Notes
                  </Link>
                  <Link
                    to="/chat"
                    className={`relative text-sm font-medium transition-colors duration-200 ${location.pathname === '/chat'
                        ? 'text-indigo-600'
                        : 'text-gray-700 hover:text-indigo-600'
                      } after:absolute after:bottom-0 after:left-0 after:h-0.5 after:bg-indigo-600 after:transition-all after:duration-300 ${location.pathname === '/chat' ? 'after:w-full' : 'after:w-0 hover:after:w-full'}`}
                  >
                    Inbox
                  </Link>
                </>
              )}
            </div>
          </div>

          {/* Right Section: Auth Buttons or User Menu */}
          <div className="flex items-center gap-4">
            {!isAuthenticated ? (
              <div className="hidden sm:flex items-center gap-3">
                <Link
                  to="/login"
                  className="inline-flex items-center justify-center px-5 py-2.5 text-sm font-semibold text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  className="inline-flex items-center justify-center px-5 py-2.5 text-sm font-semibold text-white bg-indigo-600 border border-indigo-600 rounded-lg hover:bg-indigo-700 hover:border-indigo-700 shadow-sm hover:shadow transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Register
                </Link>
              </div>
            ) : (
              <div className="relative" ref={profileRef}>
                <button
                  onClick={() => setIsProfileOpen(!isProfileOpen)}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 transition-all duration-200 group"
                  aria-label="User menu"
                  aria-expanded={isProfileOpen}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center shadow-sm group-hover:shadow-md transition-all duration-200">
                      <span className="text-sm font-semibold text-white">
                        {getUserInitials()}
                      </span>
                    </div>
                    <div className="hidden lg:flex flex-col items-start">
                      <span className="text-sm font-semibold text-gray-900">
                        {getUserDisplayName()}
                      </span>
                      <span className="text-xs text-gray-500">
                        {user?.role || 'Student'}
                      </span>
                    </div>
                  </div>
                  <svg
                    className={`hidden lg:block w-5 h-5 text-gray-400 transition-transform duration-200 ${isProfileOpen ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* Dropdown Menu */}
                {isProfileOpen && (
                  <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-200">
                    {/* User Info Section */}
                    <div className="px-4 py-3 border-b border-gray-100">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center shadow-sm">
                          <span className="text-base font-semibold text-white">
                            {getUserInitials()}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-gray-900 truncate">
                            {getUserDisplayName()}
                          </p>
                          <p className="text-xs text-gray-500 truncate">
                            {user?.email}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Menu Items */}
                    <div className="py-2">
                      <Link
                        to="/dashboard"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-150"
                      >
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                        </svg>
                        <span className="font-medium">Dashboard</span>
                      </Link>

                      <Link
                        to="/quizzes"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-150"
                      >
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                        </svg>
                        <span className="font-medium">My Quizzes</span>
                      </Link>

                      <Link
                        to="/chat"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-150"
                      >
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        <span className="font-medium">Inbox</span>
                      </Link>

                      <Link
                        to="/profile"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-150"
                      >
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        <span className="font-medium">My Profile</span>
                      </Link>

                      <Link
                        to="/settings"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-150"
                      >
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        <span className="font-medium">Settings</span>
                      </Link>

                      <Link
                        to="/#contact"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-150"
                      >
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="font-medium">Help & Support</span>
                      </Link>
                    </div>

                    {/* Sign Out Section */}
                    <div className="border-t border-gray-100 pt-2">
                      <button
                        onClick={() => {
                          setIsProfileOpen(false);
                          handleLogout();
                        }}
                        disabled={isLoggingOut}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                        <span className="font-medium">
                          {isLoggingOut ? 'Signing out...' : 'Sign out'}
                        </span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="lg:hidden p-2 rounded-lg text-slate-800 hover:bg-slate-100 transition-colors duration-200"
              aria-label="Toggle menu"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                {isMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="sm:hidden py-4 border-t border-slate-200 animate-in slide-in-from-top">
            <div className="flex flex-col gap-3">
              <Link
                to="/"
                onClick={() => setIsMenuOpen(false)}
                className={`px-4 py-2 rounded-lg font-semibold transition-all duration-200 ${location.pathname === '/'
                    ? 'bg-indigo-50 text-indigo-600'
                    : 'text-slate-800 hover:bg-slate-50'
                  }`}
              >
                Home
              </Link>
              <Link
                to="/features"
                onClick={() => setIsMenuOpen(false)}
                className={`px-4 py-2 rounded-lg font-semibold transition-all duration-200 ${location.pathname === '/features'
                    ? 'bg-indigo-50 text-indigo-600'
                    : 'text-slate-800 hover:bg-slate-50'
                  }`}
              >
                Features
              </Link>
              <Link
                to="/about"
                onClick={() => setIsMenuOpen(false)}
                className={`px-4 py-2 rounded-lg font-semibold transition-all duration-200 ${location.pathname === '/about'
                    ? 'bg-indigo-50 text-indigo-600'
                    : 'text-slate-800 hover:bg-slate-50'
                  }`}
              >
                About
              </Link>
              <Link
                to="/contact"
                onClick={() => setIsMenuOpen(false)}
                className={`px-4 py-2 rounded-lg font-semibold transition-all duration-200 ${location.pathname === '/contact'
                    ? 'bg-indigo-50 text-indigo-600'
                    : 'text-slate-800 hover:bg-slate-50'
                  }`}
              >
                Contact
              </Link>
              <Link
                to="/interest-check"
                onClick={() => setIsMenuOpen(false)}
                className={`px-4 py-2 rounded-lg font-semibold transition-all duration-200 ${location.pathname === '/interest-check'
                    ? 'bg-indigo-50 text-indigo-600'
                    : 'text-slate-800 hover:bg-slate-50'
                  }`}
              >
                Interest Check
              </Link>
              {isAuthenticated && (
                <>
                  <Link
                    to="/quizzes"
                    onClick={() => setIsMenuOpen(false)}
                    className={`px-4 py-2 rounded-lg font-semibold transition-all duration-200 ${location.pathname === '/quizzes'
                        ? 'bg-indigo-50 text-indigo-600'
                        : 'text-slate-700 hover:bg-slate-50'
                      }`}
                  >
                    Quizzes
                  </Link>
                  <Link
                    to="/chat"
                    onClick={() => setIsMenuOpen(false)}
                    className={`px-4 py-2 rounded-lg font-semibold transition-all duration-200 ${location.pathname === '/chat'
                        ? 'bg-indigo-50 text-indigo-600'
                        : 'text-slate-700 hover:bg-slate-50'
                      }`}
                  >
                    Inbox
                  </Link>
                </>
              )}

              {/* Mobile Auth Actions */}
              {!isAuthenticated && (
                <div className="pt-3 border-t border-gray-200 flex flex-col gap-3">
                  <Link
                    to="/login"
                    onClick={() => setIsMenuOpen(false)}
                    className="px-4 py-2.5 text-sm font-semibold text-gray-700 bg-white border border-gray-300 rounded-lg transition-all duration-200 hover:bg-gray-50 hover:border-gray-400 text-center active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Login
                  </Link>
                  <Link
                    to="/register"
                    onClick={() => setIsMenuOpen(false)}
                    className="px-4 py-2.5 text-sm font-semibold text-white bg-indigo-600 border border-indigo-600 rounded-lg shadow-sm transition-all duration-200 hover:bg-indigo-700 hover:border-indigo-700 hover:shadow text-center active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Register
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;

