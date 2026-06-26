import React from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import {
  BarChart3,
  LayoutDashboard,
  Users,
  FileText,
  Settings,
  Shield,
  ScrollText,
  LineChart,
  MessageSquare,
  Menu,
  X,
  LogOut,
  ChevronRight,
  Bell,
} from 'lucide-react';
import { useAdminStore } from '../../store/useAdminStore';
import clsx from 'clsx';

const navItems = [
  { to: '/admin', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/admin/users', label: 'Users', icon: Users },
  { to: '/admin/catalog', label: 'Catalog', icon: Shield },
  { to: '/admin/analytics', label: 'Analytics', icon: LineChart },
  { to: '/admin/reports', label: 'Reports', icon: FileText },
  { to: '/admin/feedback', label: 'Feedback', icon: MessageSquare },
  { to: '/admin/logs', label: 'Audit Logs', icon: ScrollText },
  { to: '/admin/settings', label: 'Settings', icon: Settings },
];

const getActiveItem = (pathname: string) => {
  // Find the most specific match
  const sorted = [...navItems].sort((a, b) => b.to.length - a.to.length);
  return sorted.find((item) =>
    item.end ? pathname === item.to : pathname.startsWith(item.to)
  );
};

const AdminLayout: React.FC = () => {
  const location = useLocation();
  const { admin, logout, fetchProfile } = useAdminStore();
  const [mobileOpen, setMobileOpen] = React.useState(false);

  React.useEffect(() => {
    if (!admin) {
      fetchProfile();
    }
  }, [admin, fetchProfile]);

  React.useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const activeItem = getActiveItem(location.pathname);

  const SidebarContent = (
    <>
      <div className="h-16 flex items-center px-6 border-b border-slate-200">
        <Link to="/admin" className="flex items-center gap-2.5 group">
          <div className="h-9 w-9 rounded-lg bg-slate-900 text-white flex items-center justify-center shadow-sm group-hover:scale-105 transition-transform">
            <BarChart3 className="h-5 w-5" />
          </div>
          <div className="flex flex-col leading-tight">
            <span className="text-[15px] font-semibold text-slate-900 tracking-tight">PLPG Admin</span>
            <span className="text-[11px] text-slate-500 font-medium">Control Center</span>
          </div>
        </Link>
      </div>

      <div className="px-4 pt-4 pb-2">
        <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-2">
          Workspace
        </p>
      </div>

      <nav className="flex-1 px-3 pb-4 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = item.end
            ? location.pathname === item.to
            : location.pathname.startsWith(item.to) && (item.to !== '/admin' || location.pathname === '/admin');
          return (
            <Link
              key={item.to}
              to={item.to}
              className={clsx(
                'group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all relative',
                active
                  ? 'bg-slate-900 text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              )}
            >
              <Icon
                className={clsx(
                  'h-[18px] w-[18px] flex-shrink-0',
                  active ? 'text-white' : 'text-slate-500 group-hover:text-slate-700'
                )}
              />
              <span className="flex-1 truncate">{item.label}</span>
              {active && <ChevronRight className="h-4 w-4 text-white/70" />}
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t border-slate-200 bg-slate-50/50">
        <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-white transition-colors">
          <div className="h-9 w-9 rounded-full bg-gradient-to-br from-slate-700 to-slate-900 text-white flex items-center justify-center font-semibold text-sm shadow-sm">
            {admin?.name?.[0]?.toUpperCase() ?? 'A'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-900 truncate">
              {admin?.name ?? 'Administrator'}
            </p>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex lg:w-64 flex-col border-r border-slate-200 bg-white sticky top-0 h-screen">
        {SidebarContent}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <button
            aria-label="Close menu"
            onClick={() => setMobileOpen(false)}
            className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm animate-in fade-in"
          />
          <aside className="relative w-72 max-w-[85vw] flex flex-col bg-white shadow-2xl animate-in slide-in-from-left">
            <button
              onClick={() => setMobileOpen(false)}
              className="absolute top-4 right-4 p-1.5 rounded-md text-slate-500 hover:bg-slate-100 z-10"
            >
              <X className="h-5 w-5" />
            </button>
            {SidebarContent}
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        <header className="sticky top-0 z-30 h-16 px-4 sm:px-6 border-b border-slate-200 bg-white/85 backdrop-blur-md flex items-center gap-3">
          <button
            onClick={() => setMobileOpen(true)}
            className="lg:hidden p-2 -ml-2 rounded-md text-slate-600 hover:bg-slate-100 transition-colors"
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="hidden sm:inline">Admin</span>
              <ChevronRight className="hidden sm:inline h-3.5 w-3.5" />
              <span className="font-medium text-slate-700">{activeItem?.label ?? 'Dashboard'}</span>
            </div>
            <h1 className="text-base sm:text-lg font-semibold text-slate-900 leading-tight truncate">
              {activeItem?.label ?? 'Dashboard'}
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <button
              className="hidden sm:inline-flex items-center justify-center h-9 w-9 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors"
              title="Notifications"
            >
              <Bell className="h-4 w-4" />
            </button>
            <div className="hidden md:flex items-center gap-2 h-9 px-3 rounded-lg border border-slate-200 bg-white">
              <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs font-medium text-slate-600">Operational</span>
            </div>
            <button
              onClick={logout}
              className="inline-flex items-center gap-1.5 h-9 px-3 sm:px-4 rounded-lg bg-slate-900 text-white text-sm font-medium hover:bg-slate-800 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-[1600px] w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
