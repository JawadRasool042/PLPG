import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  LayoutDashboard,
  Compass,
  ClipboardList,
  History,
  Map,
  Notebook,
  MessageSquare,
  Lightbulb,
  User,
  Settings,
  LogOut,
  ChevronDown,
  Menu,
  X,
  Bell,
  BookOpen,
  type LucideIcon,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import { cn } from '../lib/utils';

type NavItem = { to: string; label: string; shortLabel: string; icon: LucideIcon };

const PUBLIC_LINKS: [string, string][] = [
  ['/', 'Home'],
  ['/features', 'Features'],
  ['/about', 'About'],
  ['/contact', 'Contact'],
];

const APP_NAV_ITEMS: NavItem[] = [
  { to: '/quizzes/interest-check', label: 'Interest Check', shortLabel: 'Interest', icon: Compass },
  { to: '/quizzes', label: 'Quiz Hub', shortLabel: 'Quizzes', icon: ClipboardList },
  { to: '/quizzes/recent', label: 'Recent Quizzes', shortLabel: 'Recent', icon: History },
  { to: '/learning-path', label: 'Learning Path', shortLabel: 'Path', icon: Map },
  { to: '/notes', label: 'Notes', shortLabel: 'Notes', icon: Notebook },
  { to: '/chat', label: 'Messages & Community', shortLabel: 'Community', icon: MessageSquare },
  { to: '/feedback', label: 'Feedback', shortLabel: 'Feedback', icon: Lightbulb },
];

const PROFILE_LINKS: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', shortLabel: 'Dashboard', icon: LayoutDashboard },
  { to: '/profile', label: 'Profile', shortLabel: 'Profile', icon: User },
  { to: '/settings', label: 'Settings', shortLabel: 'Settings', icon: Settings },
];

const spring = { type: 'spring' as const, stiffness: 420, damping: 32 };
const easeOut = [0.22, 1, 0.36, 1] as const;

type Notification = { id: string; title: string; body: string; to: string };

const Navbar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout, userInterests } = useStore();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  const isActive = useCallback(
    (path: string) => {
      const current = location.pathname;
      if (path === '/') return current === '/';
      if (path === '/quizzes') {
        return current === '/quizzes' || current.startsWith('/quiz/') || current === '/ai-quiz';
      }
      if (path.startsWith('/quizzes/')) {
        return current === path || current.startsWith(`${path}/`);
      }
      return current === path || current.startsWith(`${path}/`);
    },
    [location.pathname],
  );

  const activePublicPath = useMemo(
    () => PUBLIC_LINKS.find(([to]) => isActive(to))?.[0] ?? null,
    [isActive],
  );

  const notifications = useMemo((): Notification[] => {
    if (!isAuthenticated) return [];
    const items: Notification[] = [];
    if (!userInterests?.primaryInterest) {
      items.push({
        id: 'interest',
        title: 'Complete interest assessment',
        body: 'Unlock your personalized learning path.',
        to: '/quizzes/interest-check',
      });
    }
    items.push({
      id: 'quiz',
      title: 'Practice in Quiz Hub',
      body: 'Take a quiz to refresh your recommendations.',
      to: '/quizzes',
    });
    items.push({
      id: 'path',
      title: 'Review learning path',
      body: 'Check updated courses and roadmap milestones.',
      to: '/learning-path',
    });
    return items;
  }, [isAuthenticated, userInterests?.primaryInterest]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 6);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    const onPointerDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (profileRef.current && !profileRef.current.contains(t)) setProfileOpen(false);
      if (notifRef.current && !notifRef.current.contains(t)) setNotifOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setProfileOpen(false);
        setNotifOpen(false);
        setMobileOpen(false);
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => {
    setProfileOpen(false);
    setNotifOpen(false);
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [mobileOpen]);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      navigate('/');
    } catch (e) {
      console.error('Logout error:', e);
    } finally {
      setIsLoggingOut(false);
    }
  };

  const displayName = () => {
    if (user?.firstName && user?.lastName) return `${user.firstName} ${user.lastName}`;
    if (user?.firstName) return user.firstName;
    return user?.email?.split('@')[0] || 'Student';
  };

  const initials = () => {
    if (user?.firstName && user?.lastName)
      return `${user.firstName.charAt(0)}${user.lastName.charAt(0)}`.toUpperCase();
    if (user?.firstName) return user.firstName.charAt(0).toUpperCase();
    return user?.email?.charAt(0).toUpperCase() || 'S';
  };

  const renderNavPill = (
    item: NavItem,
    layoutGroup: string,
    onClick?: () => void,
  ) => {
    const Icon = item.icon;
    const active = isActive(item.to);
    return (
      <Link
        key={item.to}
        to={item.to}
        onClick={onClick}
        title={item.label}
        aria-current={active ? 'page' : undefined}
        className={cn('nav-pill-link group', active && 'nav-pill-link--active')}
      >
        {active && (
          <motion.span
            layoutId={`${layoutGroup}-active-pill`}
            className="nav-pill-active"
            transition={spring}
          />
        )}
        <motion.span
          className="nav-pill-icon-wrap"
          whileHover={{ y: -2 }}
          transition={{ duration: 0.18 }}
        >
          <Icon className="nav-pill-icon" strokeWidth={2} aria-hidden />
        </motion.span>
        <span className="nav-pill-label">{item.shortLabel}</span>
      </Link>
    );
  };

  const renderPublicPill = (to: string, label: string, onClick?: () => void) => {
    const active = isActive(to);
    return (
      <Link
        key={to}
        to={to}
        onClick={onClick}
        aria-current={active ? 'page' : undefined}
        className={cn('nav-pill-link group', active && 'nav-pill-link--active')}
      >
        {active && (
          <motion.span
            layoutId="public-active-pill"
            className="nav-pill-active"
            transition={spring}
          />
        )}
        <span className="nav-pill-label px-0.5">{label}</span>
      </Link>
    );
  };

  return (
    <motion.header
      className={cn('nav-shell', scrolled && 'nav-shell--scrolled')}
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: easeOut }}
    >
      <nav className="nav-bar" aria-label="Main navigation">
        <div className="nav-inner">
          {/* Brand */}
          <Link to={isAuthenticated ? '/dashboard' : '/'} className="nav-brand group" aria-label="PLPG home">
            <motion.span
              className="nav-logo"
              whileHover={{ rotate: 4, scale: 1.04 }}
              transition={{ type: 'spring', stiffness: 400, damping: 18 }}
            >
              <BookOpen className="h-[1.05rem] w-[1.05rem]" strokeWidth={2.25} />
            </motion.span>
            <span className="nav-brand-name">PLPG</span>
          </Link>

          {/* Center — public or app navigation */}
          {!isAuthenticated && (
            <div className="nav-center hidden md:flex" aria-label="Website">
              <div className="nav-pill-track">
                {PUBLIC_LINKS.map(([to, label]) => renderPublicPill(to, label))}
              </div>
            </div>
          )}

          {isAuthenticated && (
            <div className="nav-center hidden lg:flex" aria-label="App pages">
              <div className="nav-pill-track nav-pill-track--app">
                {APP_NAV_ITEMS.map((item) => renderNavPill(item, 'app'))}
              </div>
            </div>
          )}

          {/* Right */}
          <div className="nav-actions">
            {isAuthenticated ? (
              <>
                <div className="relative" ref={notifRef}>
                  <motion.button
                    type="button"
                    whileTap={{ scale: 0.96 }}
                    onClick={() => setNotifOpen((o) => !o)}
                    className={cn('nav-icon-btn', notifOpen && 'nav-icon-btn--active')}
                    aria-label={`Notifications${notifications.length ? `, ${notifications.length} items` : ''}`}
                    aria-expanded={notifOpen}
                  >
                    <Bell className="h-[18px] w-[18px]" strokeWidth={2} />
                    {notifications.length > 0 && (
                      <span className="nav-notif-dot">{notifications.length > 9 ? '9+' : notifications.length}</span>
                    )}
                  </motion.button>

                  <AnimatePresence>
                    {notifOpen && (
                      <motion.div
                        className="nav-dropdown nav-dropdown--notif"
                        role="menu"
                        initial={{ opacity: 0, scale: 0.96, y: -4 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.96, y: -4 }}
                        transition={{ duration: 0.18, ease: easeOut }}
                      >
                        <p className="nav-dropdown-heading">Notifications</p>
                        <ul className="nav-notif-list">
                          {notifications.map((n) => (
                            <li key={n.id}>
                              <Link
                                to={n.to}
                                onClick={() => setNotifOpen(false)}
                                className="nav-notif-item"
                              >
                                <p className="font-medium text-foreground">{n.title}</p>
                                <p className="mt-0.5 text-xs text-muted-foreground">{n.body}</p>
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                <div className="relative" ref={profileRef}>
                  <motion.button
                    type="button"
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setProfileOpen((o) => !o)}
                    className={cn('nav-profile', profileOpen && 'nav-profile--open')}
                    aria-expanded={profileOpen}
                    aria-haspopup="true"
                    aria-label="Account menu"
                  >
                    <motion.span
                      className="nav-avatar"
                      whileHover={{ scale: 1.05, boxShadow: '0 4px 14px rgba(15,23,42,0.12)' }}
                      transition={{ duration: 0.2 }}
                    >
                      {initials()}
                    </motion.span>
                    <span className="nav-profile-text hidden xl:block">
                      <span className="nav-profile-name">{displayName()}</span>
                      <span className="nav-profile-role">{user?.role || 'Student'}</span>
                    </span>
                    <ChevronDown
                      className={cn('nav-chevron hidden xl:block', profileOpen && 'rotate-180')}
                      strokeWidth={2}
                    />
                  </motion.button>

                  <AnimatePresence>
                    {profileOpen && (
                      <motion.div
                        className="nav-dropdown nav-dropdown--profile"
                        role="menu"
                        initial={{ opacity: 0, scale: 0.96, y: -4 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.96, y: -4 }}
                        transition={{ duration: 0.18, ease: easeOut }}
                      >
                        <div className="nav-dropdown-user">
                          <span className="nav-avatar">{initials()}</span>
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold">{displayName()}</p>
                            <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
                          </div>
                        </div>
                        <div className="py-1">
                          {PROFILE_LINKS.map((item) => {
                            const Icon = item.icon;
                            const active = isActive(item.to);
                            return (
                              <Link
                                key={item.to}
                                to={item.to}
                                onClick={() => setProfileOpen(false)}
                                className={cn('nav-menu-item', active && 'nav-menu-item--active')}
                              >
                                <Icon className="h-4 w-4 shrink-0" strokeWidth={2} />
                                {item.label}
                              </Link>
                            );
                          })}
                        </div>
                        <div className="border-t border-border/80 pt-1">
                          <button
                            type="button"
                            disabled={isLoggingOut}
                            onClick={() => {
                              setProfileOpen(false);
                              void handleLogout();
                            }}
                            className="nav-menu-item nav-menu-item--danger w-full text-left"
                          >
                            <LogOut className="h-4 w-4 shrink-0" strokeWidth={2} />
                            {isLoggingOut ? 'Signing out…' : 'Sign out'}
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </>
            ) : (
              <div className="hidden items-center gap-2 sm:flex">
                <Link to="/login" className="nav-ghost-btn">
                  Log in
                </Link>
                <Link to="/register" className="nav-primary-btn">
                  Get started
                </Link>
              </div>
            )}

            <motion.button
              type="button"
              whileTap={{ scale: 0.96 }}
              onClick={() => setMobileOpen((o) => !o)}
              className={cn('nav-icon-btn', isAuthenticated ? 'lg:hidden' : 'md:hidden')}
              aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileOpen}
            >
              {mobileOpen ? <X className="h-5 w-5" strokeWidth={2} /> : <Menu className="h-5 w-5" strokeWidth={2} />}
            </motion.button>
          </div>
        </div>
      </nav>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.button
              type="button"
              className="nav-drawer-backdrop"
              aria-label="Close menu"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              className="nav-drawer"
              role="dialog"
              aria-modal="true"
              aria-label="Navigation menu"
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={spring}
            >
              {!isAuthenticated ? (
                <motion.div
                  initial="hidden"
                  animate="show"
                  variants={{
                    hidden: {},
                    show: { transition: { staggerChildren: 0.04 } },
                  }}
                >
                  <p className="nav-drawer-label">Explore</p>
                  {PUBLIC_LINKS.map(([to, label]) => (
                    <motion.div key={to} variants={{ hidden: { opacity: 0, x: 12 }, show: { opacity: 1, x: 0 } }}>
                      <Link
                        to={to}
                        onClick={() => setMobileOpen(false)}
                        className={cn('nav-drawer-link', activePublicPath === to && 'nav-drawer-link--active')}
                      >
                        {label}
                      </Link>
                    </motion.div>
                  ))}
                  <div className="mt-6 flex flex-col gap-2 border-t border-border pt-4">
                    <Link to="/login" onClick={() => setMobileOpen(false)} className="nav-ghost-btn w-full justify-center">
                      Log in
                    </Link>
                    <Link to="/register" onClick={() => setMobileOpen(false)} className="nav-primary-btn w-full justify-center">
                      Get started
                    </Link>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  initial="hidden"
                  animate="show"
                  variants={{
                    hidden: {},
                    show: { transition: { staggerChildren: 0.035 } },
                  }}
                >
                  <p className="nav-drawer-label">Navigate</p>
                  {APP_NAV_ITEMS.map((item) => {
                    const Icon = item.icon;
                    const active = isActive(item.to);
                    return (
                      <motion.div key={item.to} variants={{ hidden: { opacity: 0, x: 12 }, show: { opacity: 1, x: 0 } }}>
                        <Link
                          to={item.to}
                          onClick={() => setMobileOpen(false)}
                          className={cn('nav-drawer-link nav-drawer-link--icon', active && 'nav-drawer-link--active')}
                        >
                          <Icon className="h-4 w-4 shrink-0" strokeWidth={2} />
                          {item.label}
                        </Link>
                      </motion.div>
                    );
                  })}
                  <p className="nav-drawer-label mt-6">Account</p>
                  {PROFILE_LINKS.map((item) => {
                    const Icon = item.icon;
                    return (
                      <motion.div key={item.to} variants={{ hidden: { opacity: 0, x: 12 }, show: { opacity: 1, x: 0 } }}>
                        <Link
                          to={item.to}
                          onClick={() => setMobileOpen(false)}
                          className="nav-drawer-link nav-drawer-link--icon"
                        >
                          <Icon className="h-4 w-4 shrink-0" strokeWidth={2} />
                          {item.label}
                        </Link>
                      </motion.div>
                    );
                  })}
                  <motion.div variants={{ hidden: { opacity: 0, x: 12 }, show: { opacity: 1, x: 0 } }}>
                    <button
                      type="button"
                      onClick={() => {
                        setMobileOpen(false);
                        void handleLogout();
                      }}
                      className="nav-drawer-link nav-drawer-link--icon nav-drawer-link--danger w-full text-left"
                    >
                      <LogOut className="h-4 w-4 shrink-0" strokeWidth={2} />
                      Sign out
                    </button>
                  </motion.div>
                </motion.div>
              )}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </motion.header>
  );
};

export default Navbar;
