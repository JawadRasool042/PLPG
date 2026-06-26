import React, { useState } from 'react';
import { Save, AlertCircle, CheckCircle2, Settings as SettingsIcon, ShieldCheck, Bell } from 'lucide-react';

const AdminSettings: React.FC = () => {
  const [settings, setSettings] = useState({
    siteName: 'PLPG',
    siteDescription: 'Personalized Learning Path Generator',
    maintenanceMode: false,
    emailNotifications: true,
    twoFactorAuth: true,
    sessionTimeout: 30,
    maxLoginAttempts: 5,
  });
  const [saved, setSaved] = useState(false);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value, type } = e.target;
    const checked = (e.target as HTMLInputElement).checked;
    setSettings((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const setToggle = (name: keyof typeof settings, value: boolean) => {
    setSettings((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Page intro */}
      <div>
        <h2 className="text-2xl sm:text-3xl font-semibold text-slate-900 tracking-tight">
          Settings
        </h2>
        <p className="text-sm text-slate-600 mt-1.5">
          Manage platform configuration, security policies, and notifications.
        </p>
      </div>

      {/* Toast */}
      {saved && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-3.5 flex items-start gap-3 animate-in fade-in slide-in-from-top-2">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-emerald-900">Settings saved</p>
            <p className="text-xs text-emerald-700 mt-0.5">Your changes have been applied.</p>
          </div>
        </div>
      )}

      {/* General */}
      <SettingsSection
        icon={<SettingsIcon className="h-4 w-4" />}
        title="General"
        description="Basic platform information and operational mode."
      >
        <Field label="Site name">
          <input
            type="text"
            name="siteName"
            value={settings.siteName}
            onChange={handleChange}
            className="w-full h-10 rounded-lg border border-slate-200 px-3 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition"
          />
        </Field>

        <Field label="Site description">
          <textarea
            name="siteDescription"
            value={settings.siteDescription}
            onChange={handleChange}
            rows={3}
            className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition resize-none"
          />
        </Field>

        <ToggleRow
          checked={settings.maintenanceMode}
          onChange={(v) => setToggle('maintenanceMode', v)}
          title="Maintenance mode"
          description="When enabled, end-users will see a maintenance message until disabled."
          warning
        />
      </SettingsSection>

      {/* Security */}
      <SettingsSection
        icon={<ShieldCheck className="h-4 w-4" />}
        title="Security"
        description="Authentication, session, and access policies."
      >
        <ToggleRow
          checked={settings.twoFactorAuth}
          onChange={(v) => setToggle('twoFactorAuth', v)}
          title="Require two-factor authentication"
          description="Enforce 2FA for all administrator accounts."
        />

        <Field label="Session timeout (minutes)">
          <input
            type="number"
            name="sessionTimeout"
            value={settings.sessionTimeout}
            onChange={handleChange}
            min={5}
            max={480}
            className="w-full h-10 rounded-lg border border-slate-200 px-3 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition tabular-nums"
          />
        </Field>

        <Field label="Max login attempts">
          <input
            type="number"
            name="maxLoginAttempts"
            value={settings.maxLoginAttempts}
            onChange={handleChange}
            min={1}
            max={20}
            className="w-full h-10 rounded-lg border border-slate-200 px-3 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition tabular-nums"
          />
        </Field>
      </SettingsSection>

      {/* Notifications */}
      <SettingsSection
        icon={<Bell className="h-4 w-4" />}
        title="Notifications"
        description="Channel preferences for system alerts."
      >
        <ToggleRow
          checked={settings.emailNotifications}
          onChange={(v) => setToggle('emailNotifications', v)}
          title="Email notifications"
          description="Send email alerts for important events and security incidents."
        />
      </SettingsSection>

      {/* Action bar */}
      <div className="sticky bottom-4 flex items-center gap-2 rounded-xl border border-slate-200 bg-white/95 backdrop-blur-md px-4 py-3 shadow-sm">
        <p className="text-xs text-slate-500 flex-1 hidden sm:block">
          Changes will apply once saved.
        </p>
        <button className="h-9 px-4 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors">
          Cancel
        </button>
        <button
          onClick={handleSave}
          className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-slate-900 text-white text-sm font-medium hover:bg-slate-800 transition-colors"
        >
          <Save className="h-4 w-4" />
          Save changes
        </button>
      </div>
    </div>
  );
};

const SettingsSection: React.FC<{
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}> = ({ icon, title, description, children }) => (
  <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
    <div className="px-5 sm:px-6 py-4 border-b border-slate-100 flex items-start gap-3">
      <div className="h-9 w-9 rounded-lg bg-slate-50 text-slate-600 ring-1 ring-slate-200 flex items-center justify-center flex-shrink-0">
        {icon}
      </div>
      <div className="min-w-0">
        <h3 className="text-[15px] font-semibold text-slate-900 tracking-tight">{title}</h3>
        <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{description}</p>
      </div>
    </div>
    <div className="p-5 sm:p-6 space-y-5">{children}</div>
  </div>
);

const Field: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div>
    <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
      {label}
    </label>
    {children}
  </div>
);

const ToggleRow: React.FC<{
  checked: boolean;
  onChange: (v: boolean) => void;
  title: string;
  description: string;
  warning?: boolean;
}> = ({ checked, onChange, title, description, warning }) => (
  <div
    className={`flex items-start gap-3 p-3.5 rounded-lg border ${
      warning && checked
        ? 'border-amber-200 bg-amber-50'
        : 'border-slate-200 bg-slate-50/50'
    }`}
  >
    {warning && checked && (
      <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
    )}
    <div className="flex-1 min-w-0">
      <p className={`text-sm font-semibold ${warning && checked ? 'text-amber-900' : 'text-slate-900'}`}>
        {title}
      </p>
      <p className={`text-xs mt-0.5 leading-relaxed ${warning && checked ? 'text-amber-700' : 'text-slate-500'}`}>
        {description}
      </p>
    </div>
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500/30 ${
        checked ? 'bg-indigo-600' : 'bg-slate-300'
      }`}
    >
      <span
        className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform ${
          checked ? 'translate-x-5' : 'translate-x-0.5'
        }`}
      />
    </button>
  </div>
);

export default AdminSettings;
