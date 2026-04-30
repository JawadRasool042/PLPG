import React, { useState } from 'react';
import { Save, AlertCircle, CheckCircle2 } from 'lucide-react';

const AdminSettings: React.FC = () => {
  const [settings, setSettings] = useState({
    siteName: 'PLPG',
    siteDescription: 'Personalized Learning Path Generator',
    maintenanceMode: false,
    emailNotifications: true,
    twoFactorAuth: true,
    sessionTimeout: 30,
    maxLoginAttempts: 5
  });
  const [saved, setSaved] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    const checked = (e.target as HTMLInputElement).checked;
    
    setSettings(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Header */}
      <div>
        <p className="text-sm font-medium text-slate-500">Configure system settings</p>
        <h1 className="text-3xl font-bold text-slate-900 mt-1">Settings</h1>
        <p className="text-sm text-slate-600 mt-1">Manage platform configuration and preferences</p>
      </div>

      {/* Success Message */}
      {saved && (
        <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-4 flex items-start gap-3">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-emerald-900">Settings saved successfully</p>
            <p className="text-sm text-emerald-700 mt-1">Your changes have been applied</p>
          </div>
        </div>
      )}

      {/* General Settings */}
      <div className="rounded-2xl border border-slate-200 bg-white p-8">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">General Settings</h2>
        
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Site Name</label>
            <input
              type="text"
              name="siteName"
              value={settings.siteName}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-900 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Site Description</label>
            <textarea
              name="siteDescription"
              value={settings.siteDescription}
              onChange={handleChange}
              rows={3}
              className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-900 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all resize-none"
            />
          </div>

          <div className="flex items-center gap-3 p-4 rounded-lg bg-amber-50 border border-amber-200">
            <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0" />
            <div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  name="maintenanceMode"
                  checked={settings.maintenanceMode}
                  onChange={handleChange}
                  className="rounded"
                />
                <span className="font-semibold text-amber-900">Enable Maintenance Mode</span>
              </label>
              <p className="text-sm text-amber-700 mt-1">Users will see a maintenance message</p>
            </div>
          </div>
        </div>
      </div>

      {/* Security Settings */}
      <div className="rounded-2xl border border-slate-200 bg-white p-8">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">Security Settings</h2>
        
        <div className="space-y-6">
          <div>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                name="twoFactorAuth"
                checked={settings.twoFactorAuth}
                onChange={handleChange}
                className="rounded"
              />
              <span className="font-semibold text-slate-700">Require Two-Factor Authentication</span>
            </label>
            <p className="text-sm text-slate-600 mt-2 ml-8">Enforce 2FA for all admin accounts</p>
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Session Timeout (minutes)</label>
            <input
              type="number"
              name="sessionTimeout"
              value={settings.sessionTimeout}
              onChange={handleChange}
              min="5"
              max="480"
              className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-900 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Max Login Attempts</label>
            <input
              type="number"
              name="maxLoginAttempts"
              value={settings.maxLoginAttempts}
              onChange={handleChange}
              min="1"
              max="20"
              className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-900 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
            />
          </div>
        </div>
      </div>

      {/* Notification Settings */}
      <div className="rounded-2xl border border-slate-200 bg-white p-8">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">Notification Settings</h2>
        
        <div className="space-y-6">
          <div>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                name="emailNotifications"
                checked={settings.emailNotifications}
                onChange={handleChange}
                className="rounded"
              />
              <span className="font-semibold text-slate-700">Enable Email Notifications</span>
            </label>
            <p className="text-sm text-slate-600 mt-2 ml-8">Send email alerts for important events</p>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-indigo-600 text-white font-semibold hover:bg-indigo-700 transition-colors"
        >
          <Save className="h-5 w-5" />
          Save Settings
        </button>
        <button className="px-6 py-3 rounded-lg border border-slate-200 text-slate-700 font-semibold hover:bg-slate-50 transition-colors">
          Cancel
        </button>
      </div>
    </div>
  );
};

export default AdminSettings;
