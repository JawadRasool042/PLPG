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
  Lock,
  type LucideIcon,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import { cn } from '../lib/utils';
import { getUserPerformance, type UserPerformance } from '../services/quizService';
import { getEffectivePrimaryInterest } from '../utils/interestDisplay';
import {
  canAccessLearningPath,
  hasCompletedInterestCheck,
} from '../utils/learningPathGate';

type NavItem = { to: string; label: string; shortLabel: string; icon: LucideIcon };

type NavLinkDef = {
  to: string;
  label: string;
  hint: string;
  icon: LucideIcon;
};

const PUBLIC_LINKS: [string, string][] = [
  ['/', 'Home'],
  ['/features', 'Features'],
  ['/about', 'About'],
  ['/contact', 'Contact'],
];

const HOME_LINK: NavItem = {
  to: '/home',
  label: 'Home',
  shortLabel: 'Home',
  icon: LayoutDashboard,
};

const COMMUNITY_LINK: NavItem = {
  to: '/chat',
  label: 'Community',
  shortLabel: 'Community',
  icon: MessageSquare,
};

const PRACTICE_LINKS: NavLinkDef[] = [
  {
    to: '/quizzes',
    label: 'Quiz Hub',
    hint: 'Start AI quizzes by topic and difficulty',
    icon: ClipboardList,
  },
  {
    to: '/quizzes/recent',
    label: 'Recent Quizzes',
    hint: 'Review scores and past attempts',
    icon: History,
  },
];

const LEARN_LINKS: NavLinkDef[] = [
  {
    to: '/learning-path',
    label: 'Learning Path',
    hint: 'Your roadmap, courses, and milestones',
    icon: Map,
  },
  {
    to: '/notes',
    label: 'Notes',
    hint: 'Study notes organized by domain',
    icon: Notebook,
  },
  {
    to: '/quizzes/interest-check',
    label: 'My Interests',
    hint: 'Rate domains that matter to you',
    icon: Compass,
  },
];

const ACCOUNT_LINKS: NavItem[] = [
  { to: '/profile', label: 'Profile', shortLabel: 'Profile', icon: User },
  { to: '/settings', label: 'Settings', shortLabel: 'Settings', icon: Settings },
  { to: '/feedback', label: 'Feedback & support', shortLabel: 'Feedback', icon: Lightbulb },
];

const spring = { type: 'spring' as const, stiffness: 420, damping: 32 };
const easeOut = [0.22, 1, 0.36, 1] as const;

type Notification = { id: string; title: string; body: string; to: string };

type ItemBadge = 'complete' | 'lock' | null;

const readNotifsStorageKey = (userId: string) => `plpg_read_notifs_${userId}`;

const loadReadNotifIds = (userId: string | undefined): Set<string> => {
  if (!userId) return new Set();
  try {
    const raw = localStorage.getItem(readNotifsStorageKey(userId));
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((id) => typeof id === 'string'));
  } catch {
    return new Set();
  }
};

const persistReadNotifIds = (userId: string | undefined, ids: Set<string>) => {
  if (!userId) return;
  try {
    localStorage.setItem(readNotifsStorageKey(userId), JSON.stringify([...ids]));
  } catch {
    // ignore quota / private mode
  }
};

const Navbar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout, userInterests, hasCompletedOnboarding } = useStore();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [practiceOpen, setPracticeOpen] = useState(false);
  const [learnOpen, setLearnOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [quizPerformance, setQuizPerformance] = useState<UserPerformance | null>(null);
  const [readNotifIds, setReadNotifIds] = useState<Set<string>>(() => new Set());
  const profileRef = useRef<HTMLDivElement>(null);
  const practiceRef = useRef<HTMLDivElement>(null);
  const learnRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  const interestDone = hasCompletedInterestCheck(hasCompletedOnboarding, userInterests);
  const pathUnlocked = canAccessLearningPath(
    hasCompletedOnboarding,
    userInterests,
    quizPerformance,
  );

  const closeAllDropdowns = useCallback(() => {
    setProfileOpen(false);
    setPracticeOpen(false);
    setLearnOpen(false);
    setNotifOpen(false);
  }, []);

  const isPathActive = useCallback(
    (path: string) => {
      const current = location.pathname;
      if (path === '/') return current === '/';
      if (path === '/home') return current === '/home' || current === '/dashboard';
      if (path === '/quizzes') {
        return (
          current === '/quizzes'
          || current.startsWith('/quiz/')
          || current === '/ai-quiz'
          || current.startsWith('/remediation/')
        );
      }
      if (path.startsWith('/quizzes/')) {
        return current === path || current.startsWith(`${path}/`);
      }
      return current === path || current.startsWith(`${path}/`);
    },
    [location.pathname],
  );

  const isPracticeActive = useMemo(() => {
    const current = location.pathname;
    return (
      current === '/quizzes'
      || current.startsWith('/quiz/')
      || current === '/ai-quiz'
      || current.startsWith('/remediation/')
      || current === '/quizzes/recent'
      || current.startsWith('/quizzes/recent/')
    );
  }, [location.pathname]);

  const isLearnActive = useMemo(
    () =>
      isPathActive('/learning-path')
      || isPathActive('/notes')
      || isPathActive('/quizzes/interest-check'),
    [isPathActive],
  );

  const activePublicPath = useMemo(
    () => PUBLIC_LINKS.find(([to]) => isPathActive(to))?.[0] ?? null,
    [isPathActive],
  );

  const getLinkBadge = (to: string): ItemBadge => {
    if (to === '/quizzes/interest-check' && !interestDone) return 'complete';
    if (to === '/learning-path' && !pathUnlocked) return 'lock';
    return null;
  };

  useEffect(() => {
    if (!isAuthenticated) {
      setQuizPerformance(null);
      return;
    }
    let cancelled = false;
    getUserPerformance()
      .then((perf) => {
        if (!cancelled) setQuizPerformance(perf);
      })
      .catch(() => {
        if (!cancelled) setQuizPerformance(null);
      });
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, location.pathname]);

  const notifications = useMemo((): Notification[] => {
    if (!isAuthenticated) return [];
    if (!interestDone) {
      return [
        {
          id: 'interest',
          title: 'Set your interests',
          body: 'Rate domains under Learn → My Interests.',
          to: '/quizzes/interest-check',
        },
      ];
    }
    if (!pathUnlocked) {
      return [
        {
          id: 'quiz',
          title: 'Take your first quiz',
          body: 'Open Practice → Quiz Hub to unlock your path.',
          to: '/quizzes',
        },
      ];
    }
    const primary = getEffectivePrimaryInterest(userInterests);
    return [
      {
        id: 'path',
        title: 'Continue your learning path',
        body: primary
          ? `Pick up your ${primary} roadmap next.`
          : 'Review courses and milestones.',
        to: '/learning-path',
      },
    ];
  }, [isAuthenticated, interestDone, pathUnlocked, userInterests]);

  useEffect(() => {
    setReadNotifIds(loadReadNotifIds(user?.id));
  }, [user?.id]);

  const markNotifRead = useCallback(
    (id: string) => {
      setReadNotifIds((prev) => {
        if (prev.has(id)) return prev;
        const next = new Set(prev);
        next.add(id);
        persistReadNotifIds(user?.id, next);
        return next;
      });
    },
    [user?.id],
  );

  const markAllNotifsRead = useCallback(() => {
    const allIds = new Set(notifications.map((n) => n.id));
    setReadNotifIds(allIds);
    persistReadNotifIds(user?.id, allIds);
  }, [notifications, user?.id]);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !readNotifIds.has(n.id)).length,
    [notifications, readNotifIds],
  );

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
      if (practiceRef.current && !practiceRef.current.contains(t)) setPracticeOpen(false);
      if (learnRef.current && !learnRef.current.contains(t)) setLearnOpen(false);
      if (notifRef.current && !notifRef.current.contains(t)) setNotifOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeAllDropdowns();
        setMobileOpen(false);
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [closeAllDropdowns]);

  useEffect(() => {
    closeAllDropdowns();
    setMobileOpen(false);
  }, [location.pathname, closeAllDropdowns]);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
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
    options?: { onClick?: () => void },
  ) => {
    const Icon = item.icon;
    const active = isPathActive(item.to);
    return (
      <Link
        key={item.to}
        to={item.to}
        onClick={options?.onClick}
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
    const active = isPathActive(to);
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

  const renderRichMenuItem = (item: NavLinkDef, onClose: () => void) => {
    const Icon = item.icon;
    const active = isPathActive(item.to);
    const badge = getLinkBadge(item.to);
    return (
      <Link
        key={item.to}
        to={item.to}
        onClick={onClose}
        className={cn('nav-menu-item nav-menu-item--rich', active && 'nav-menu-item--active')}
      >
        <Icon className="h-4 w-4 shrink-0 mt-0.5" strokeWidth={2} />
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2">
            <span className="font-medium">{item.label}</span>
            {badge === 'complete' && <span className="nav-more-badge">Start here</span>}
            {badge === 'lock' && <Lock className="h-3 w-3 opacity-60" strokeWidth={2.5} aria-hidden />}
          </span>
          <span className="block text-xs text-muted-foreground leading-snug mt-0.5">{item.hint}</span>
        </span>
      </Link>
    );
  };

  const renderNavDropdown = (
    ref: React.RefObject<HTMLDivElement | null>,
    label: string,
    shortLabel: string,
    icon: LucideIcon,
    items: NavLinkDef[],
    isOpen: boolean,
    isGroupActive: boolean,
    onToggle: () => void,
    showAttentionDot?: boolean,
  ) => {
    const Icon = icon;
    return (
      <div className="relative" ref={ref}>
        <button
          type="button"
          onClick={onToggle}
          className={cn(
            'nav-pill-link group',
            (isOpen || isGroupActive) && 'nav-pill-link--active',
          )}
          aria-expanded={isOpen}
          aria-haspopup="true"
          aria-label={`${label} menu`}
        >
          {(isOpen || isGroupActive) && <span className="nav-pill-active" aria-hidden />}
          <motion.span
            className="nav-pill-icon-wrap relative"
            whileHover={{ y: -2 }}
            transition={{ duration: 0.18 }}
          >
            <Icon className="nav-pill-icon" strokeWidth={2} aria-hidden />
            {showAttentionDot && <span className="nav-pill-attention" aria-hidden />}
          </motion.span>
          <span className="nav-pill-label">{shortLabel}</span>
          <ChevronDown
            className={cn('nav-pill-chevron relative z-[1]', isOpen && 'rotate-180')}
            strokeWidth={2}
          />
        </button>

        <AnimatePresence>
          {isOpen && (
            <motion.div
              className="nav-dropdown nav-dropdown--group"
              role="menu"
              initial={{ opacity: 0, scale: 0.96, y: -4 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: -4 }}
              transition={{ duration: 0.18, ease: easeOut }}
            >
              <p className="nav-dropdown-heading">{label}</p>
              <div className="py-1">
                {items.map((item) => renderRichMenuItem(item, closeAllDropdowns))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  };

  const renderDrawerRichLink = (item: NavLinkDef, onClose: () => void) => {
    const Icon = item.icon;
    const active = isPathActive(item.to);
    const badge = getLinkBadge(item.to);
    return (
      <Link
        to={item.to}
        onClick={onClose}
        className={cn('nav-drawer-link nav-drawer-link--rich', active && 'nav-drawer-link--active')}
      >
        <Icon className="h-4 w-4 shrink-0 mt-0.5" strokeWidth={2} />
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2">
            <span className="font-medium">{item.label}</span>
            {badge === 'complete' && <span className="nav-more-badge">Start here</span>}
            {badge === 'lock' && <Lock className="h-3.5 w-3.5 opacity-60" strokeWidth={2} />}
          </span>
          <span className="block text-xs text-muted-foreground mt-0.5">{item.hint}</span>
        </span>
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
          <Link to={isAuthenticated ? '/home' : '/'} className="nav-brand group" aria-label="PLPG home">
            <motion.span
              className="nav-logo"
              whileHover={{ rotate: 4, scale: 1.04 }}
              transition={{ type: 'spring', stiffness: 400, damping: 18 }}
            >
              <BookOpen className="h-[1.05rem] w-[1.05rem]" strokeWidth={2.25} />
            </motion.span>
            <span className="nav-brand-name">PLPG</span>
          </Link>

          {!isAuthenticated && (
            <div className="nav-center hidden md:flex" aria-label="Website">
              <div className="nav-pill-track">
                {PUBLIC_LINKS.map(([to, label]) => renderPublicPill(to, label))}
              </div>
            </div>
          )}

          {isAuthenticated && (
            <div className="nav-center hidden md:flex" aria-label="App pages">
              <div className="nav-pill-track nav-pill-track--app">
                {renderNavPill(HOME_LINK, 'app')}
                {renderNavDropdown(
                  practiceRef,
                  'Practice',
                  'Practice',
                  ClipboardList,
                  PRACTICE_LINKS,
                  practiceOpen,
                  isPracticeActive,
                  () => {
                    setPracticeOpen((o) => !o);
                    setLearnOpen(false);
                    setProfileOpen(false);
                    setNotifOpen(false);
                  },
                  !interestDone,
                )}
                {renderNavDropdown(
                  learnRef,
                  'Learn',
                  'Learn',
                  Map,
                  LEARN_LINKS,
                  learnOpen,
                  isLearnActive,
                  () => {
                    setLearnOpen((o) => !o);
                    setPracticeOpen(false);
                    setProfileOpen(false);
                    setNotifOpen(false);
                  },
                )}
                {renderNavPill(COMMUNITY_LINK, 'app')}
              </div>
            </div>
          )}

          <div className="nav-actions">
            {isAuthenticated ? (
              <>
                <div className="relative" ref={notifRef}>
                  <motion.button
                    type="button"
                    whileTap={{ scale: 0.96 }}
                    onClick={() => {
                      setNotifOpen((o) => !o);
                      setPracticeOpen(false);
                      setLearnOpen(false);
                      setProfileOpen(false);
                    }}
                    className={cn('nav-icon-btn', notifOpen && 'nav-icon-btn--active')}
                    aria-label={`Next step${unreadCount ? `, ${unreadCount} unread` : ''}`}
                    aria-expanded={notifOpen}
                  >
                    <Bell className="h-[18px] w-[18px]" strokeWidth={2} />
                    {unreadCount > 0 && (
                      <span className="nav-notif-dot">{unreadCount > 9 ? '9+' : unreadCount}</span>
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
                        <div className="nav-dropdown-heading-row">
                          <p className="nav-dropdown-heading">Your next step</p>
                          {unreadCount > 0 && (
                            <button
                              type="button"
                              onClick={markAllNotifsRead}
                              className="nav-notif-mark-all"
                            >
                              Mark all as read
                            </button>
                          )}
                        </div>
                        <ul className="nav-notif-list">
                          {notifications.map((n) => {
                            const isRead = readNotifIds.has(n.id);
                            return (
                              <li key={n.id}>
                                <Link
                                  to={n.to}
                                  onClick={() => {
                                    markNotifRead(n.id);
                                    setNotifOpen(false);
                                  }}
                                  className={cn('nav-notif-item', isRead && 'nav-notif-item--read')}
                                >
                                  <p className="font-medium text-foreground">{n.title}</p>
                                  <p className="mt-0.5 text-xs text-muted-foreground">{n.body}</p>
                                </Link>
                              </li>
                            );
                          })}
                        </ul>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                <div className="relative" ref={profileRef}>
                  <motion.button
                    type="button"
                    whileTap={{ scale: 0.98 }}
                    onClick={() => {
                      setProfileOpen((o) => !o);
                      setPracticeOpen(false);
                      setLearnOpen(false);
                      setNotifOpen(false);
                    }}
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
                      <span className="nav-profile-role">Account</span>
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
                        <p className="nav-dropdown-section-label">Your account</p>
                        <div className="py-1">
                          {ACCOUNT_LINKS.map((item) => {
                            const Icon = item.icon;
                            const active = isPathActive(item.to);
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
              className="nav-icon-btn md:hidden"
              aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileOpen}
            >
              {mobileOpen ? <X className="h-5 w-5" strokeWidth={2} /> : <Menu className="h-5 w-5" strokeWidth={2} />}
            </motion.button>
          </div>
        </div>
      </nav>

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
                  <p className="nav-drawer-label">Overview</p>
                  <motion.div variants={{ hidden: { opacity: 0, x: 12 }, show: { opacity: 1, x: 0 } }}>
                    <Link
                      to={HOME_LINK.to}
                      onClick={() => setMobileOpen(false)}
                      className={cn(
                        'nav-drawer-link nav-drawer-link--icon',
                        isPathActive(HOME_LINK.to) && 'nav-drawer-link--active',
                      )}
                    >
                      <LayoutDashboard className="h-4 w-4 shrink-0" strokeWidth={2} />
                      {HOME_LINK.label}
                    </Link>
                  </motion.div>
                  <motion.div variants={{ hidden: { opacity: 0, x: 12 }, show: { opacity: 1, x: 0 } }}>
                    <Link
                      to={COMMUNITY_LINK.to}
                      onClick={() => setMobileOpen(false)}
                      className={cn(
                        'nav-drawer-link nav-drawer-link--icon',
                        isPathActive(COMMUNITY_LINK.to) && 'nav-drawer-link--active',
                      )}
                    >
                      <MessageSquare className="h-4 w-4 shrink-0" strokeWidth={2} />
                      {COMMUNITY_LINK.label}
                    </Link>
                  </motion.div>

                  <p className="nav-drawer-label mt-5">Practice — quizzes & review</p>
                  {PRACTICE_LINKS.map((item) => (
                    <motion.div key={item.to} variants={{ hidden: { opacity: 0, x: 12 }, show: { opacity: 1, x: 0 } }}>
                      {renderDrawerRichLink(item, () => setMobileOpen(false))}
                    </motion.div>
                  ))}

                  <p className="nav-drawer-label mt-5">Learn — path & study</p>
                  {LEARN_LINKS.map((item) => (
                    <motion.div key={item.to} variants={{ hidden: { opacity: 0, x: 12 }, show: { opacity: 1, x: 0 } }}>
                      {renderDrawerRichLink(item, () => setMobileOpen(false))}
                    </motion.div>
                  ))}

                  <p className="nav-drawer-label mt-5">Account</p>
                  {ACCOUNT_LINKS.map((item) => {
                    const Icon = item.icon;
                    const active = isPathActive(item.to);
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
