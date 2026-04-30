import React from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import { BarChart3, LayoutDashboard, Users, FileText, Settings, BookOpen, Activity, Shield, ScrollText, LineChart } from 'lucide-react';
import { useAdminStore } from '../../store/useAdminStore';
import clsx from 'clsx';

const navItems = [
  { to: '/admin', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/admin/users', label: 'Users', icon: Users },
  { to: '/admin/content', label: 'Content', icon: BookOpen },
  { to: '/admin/learning-paths', label: 'Learning Paths', icon: Shield },
  { to: '/admin/analytics', label: 'Analytics', icon: LineChart },
  { to: '/admin/reports', label: 'Reports', icon: FileText },
  { to: '/admin/logs', label: 'Logs', icon: ScrollText },
  { to: '/admin/settings', label: 'Settings', icon: Settings },
];

const AdminLayout: React.FC = () => {
  const location = useLocation();
  const { admin, logout, fetchProfile } = useAdminStore();

  React.useEffect(() => {
    if (!admin) {
      fetchProfile();
    }
  }, [admin, fetchProfile]);

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <aside className="hidden md:flex w-64 flex-col border-r border-slate-200 bg-white">
        <div className="h-16 flex items-center px-6 border-b border-slate-200">
          <div className="flex items-center gap-2 text-indigo-600 font-semibold text-lg">
            <BarChart3 className="h-6 w-6" />
            <span>PLPG Admin</span>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  active
                    ? 'bg-indigo-50 text-indigo-700 border border-indigo-100'
                    : 'text-slate-600 hover:bg-slate-100'
                )}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-slate-200">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-semibold">
              {admin?.name?.[0] ?? 'A'}
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-900">{admin?.name}</p>
              <p className="text-xs text-slate-500">{admin?.role?.name}</p>
            </div>
            <button
              onClick={logout}
              className="text-xs text-slate-500 hover:text-indigo-600"
            >
              Logout
            </button>
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col">
        <header className="h-16 px-4 md:px-6 border-b border-slate-200 bg-white flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500">Personalized Learning Path Generator</p>
            <h1 className="text-lg font-semibold text-slate-900">Admin Panel</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 text-slate-600 text-sm">
              <Activity className="h-4 w-4" />
              <span>Secure • RBAC • Audit</span>
            </div>
            <button
              onClick={logout}
              className="px-3 py-1.5 rounded-lg bg-slate-900 text-white text-sm hover:bg-indigo-600 transition-colors"
            >
              Logout
            </button>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
