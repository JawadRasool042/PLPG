import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { API_BASE_URL } from '../../config/apiBase';

interface SettingsData {
  email: string;
  first_name: string;
  last_name: string;
  preferences: { theme: 'light' | 'dark' | 'auto'; language: string; timezone: string };
  notifications: { email: boolean; quizReminders: boolean; progressUpdates: boolean; newsletter: boolean };
  privacy: { profileVisibility: 'public' | 'private' | 'friends'; showEmail: boolean };
}

const Settings: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, logout, theme, setTheme } = useStore();
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState<'general' | 'notifications' | 'privacy' | 'security'>('general');
  const [passwordData, setPasswordData] = useState({ current_password: '', new_password: '', confirm_password: '' });
  const [changingPassword, setChangingPassword] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    fetchSettings();
  }, [isAuthenticated, navigate]);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('plpg_access_token');
      const response = await fetch(`${API_BASE_URL}/settings`, { headers: { 'Authorization': `Bearer ${token}` } });
      if (!response.ok) throw new Error('Failed to fetch settings');
      const data = await response.json();
      setSettings({
        email: data.email || '',
        first_name: data.first_name || '',
        last_name: data.last_name || '',
        preferences: { theme: theme, language: data.preferences?.language || 'en', timezone: data.preferences?.timezone || 'UTC' },
        notifications: { email: data.notifications?.email ?? true, quizReminders: data.notifications?.quizReminders ?? true, progressUpdates: data.notifications?.progressUpdates ?? true, newsletter: data.notifications?.newsletter ?? false },
        privacy: { profileVisibility: data.privacy?.profileVisibility || 'public', showEmail: data.privacy?.showEmail ?? false }
      });
    } catch (err: any) {
      setError(err.message || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSettingsChange = (category: keyof SettingsData, key: string, value: any) => {
    if (!settings) return;
    
    // Handle theme change separately to update store
    if (category === 'preferences' && key === 'theme') {
      setTheme(value as 'light' | 'dark' | 'auto');
    }
    
    setSettings(prev => prev ? { ...prev, [category]: { ...(prev[category] as any), [key]: value } } : prev);
  };

  const handleSaveSettings = async () => {
    try {
      setSaving(true);
      const token = localStorage.getItem('plpg_access_token');
      const response = await fetch(`${API_BASE_URL}/settings`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ preferences: settings?.preferences, notifications: settings?.notifications, privacy: settings?.privacy })
      });
      if (!response.ok) throw new Error('Failed to update settings');
      setSuccess('Settings saved successfully!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordData.new_password !== passwordData.confirm_password) {
      setError('Passwords do not match');
      return;
    }
    try {
      setChangingPassword(true);
      const token = localStorage.getItem('plpg_access_token');
      const response = await fetch(`${API_BASE_URL}/settings/password`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(passwordData)
      });
      if (!response.ok) throw new Error('Failed to change password');
      setSuccess('Password changed successfully!');
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to change password');
    } finally {
      setChangingPassword(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmation !== 'DELETE') {
      setError('Please type DELETE to confirm');
      return;
    }
    try {
      setDeleting(true);
      const token = localStorage.getItem('plpg_access_token');
      const response = await fetch(`${API_BASE_URL}/account`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: deletePassword, confirmation: deleteConfirmation })
      });
      if (!response.ok) throw new Error('Failed to delete account');
      await logout();
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Failed to delete account');
      setDeleting(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8 space-y-3">
          <div className="h-10 bg-slate-200 dark:bg-slate-700 rounded-lg w-48 animate-pulse"></div>
          <div className="h-6 bg-slate-200 dark:bg-slate-700 rounded-lg w-64 animate-pulse"></div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-1">
            <LoadingSkeleton variant="card" />
          </div>
          <div className="lg:col-span-3">
            <LoadingSkeleton variant="card" count={2} />
          </div>
        </div>
      </div>
    </div>
  );
  if (!settings) return <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center"><p className="text-gray-700 dark:text-gray-300">Settings unavailable</p></div>;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold text-slate-900 dark:text-white mb-2">Settings</h1>
        <p className="text-slate-600 dark:text-slate-400 mb-8">Manage your account preferences</p>

        {success && <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg text-green-800 dark:text-green-200">{success}</div>}
        {error && <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-800 dark:text-red-200">{error}</div>}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-100 dark:border-slate-700 overflow-hidden shadow">
              <nav className="flex flex-col">
                {[{ id: 'general', name: 'General' }, { id: 'notifications', name: 'Notifications' }, { id: 'privacy', name: 'Privacy' }, { id: 'security', name: 'Security' }].map((tab) => (
                  <button key={tab.id} onClick={() => setActiveTab(tab.id as any)} className={`px-6 py-4 text-left font-semibold transition ${activeTab === tab.id ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 border-l-4 border-indigo-600' : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'}`}>
                    {tab.name}
                  </button>
                ))}
              </nav>
            </div>
          </div>

          <div className="lg:col-span-3">
            {activeTab === 'general' && (
              <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-100 dark:border-slate-700 p-6 shadow">
                <h2 className="text-xl font-semibold mb-6 dark:text-white">General Preferences</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Theme</label>
                    <select value={theme} onChange={(e) => handleSettingsChange('preferences', 'theme', e.target.value)} className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-slate-700 dark:text-white rounded-lg">
                      <option value="light">Light</option>
                      <option value="dark">Dark</option>
                      <option value="auto">Auto</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Language</label>
                    <select value={settings.preferences.language} onChange={(e) => handleSettingsChange('preferences', 'language', e.target.value)} className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-slate-700 dark:text-white rounded-lg">
                      <option value="en">English</option>
                      <option value="es">Spanish</option>
                      <option value="fr">French</option>
                    </select>
                  </div>
                </div>
                <button onClick={handleSaveSettings} disabled={saving} className="mt-6 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-100 dark:border-slate-700 p-6 shadow">
                <h2 className="text-xl font-semibold mb-6 dark:text-white">Notifications</h2>
                <div className="space-y-4">
                  {[{ key: 'email', label: 'Email' }, { key: 'quizReminders', label: 'Quiz Reminders' }, { key: 'progressUpdates', label: 'Progress' }, { key: 'newsletter', label: 'Newsletter' }].map((item) => (
                    <div key={item.key} className="flex items-center justify-between p-4 border dark:border-slate-600 rounded-lg">
                      <span className="font-medium dark:text-white">{item.label}</span>
                      <input type="checkbox" checked={settings.notifications[item.key as keyof typeof settings.notifications]} onChange={(e) => handleSettingsChange('notifications', item.key, e.target.checked)} className="w-5 h-5" />
                    </div>
                  ))}
                </div>
                <button onClick={handleSaveSettings} disabled={saving} className="mt-6 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </div>
            )}

            {activeTab === 'privacy' && (
              <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-100 dark:border-slate-700 p-6 shadow">
                <h2 className="text-xl font-semibold mb-6 dark:text-white">Privacy</h2>
                <div className="space-y-4">
                  {[{ value: 'public', label: 'Public' }, { value: 'friends', label: 'Friends Only' }, { value: 'private', label: 'Private' }].map((option) => (
                    <button key={option.value} onClick={() => handleSettingsChange('privacy', 'profileVisibility', option.value)} className={`w-full text-left p-4 rounded-lg border-2 dark:text-white ${settings.privacy.profileVisibility === option.value ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/30' : 'border-gray-200 dark:border-slate-600'}`}>
                      {option.label}
                    </button>
                  ))}
                </div>
                <button onClick={handleSaveSettings} disabled={saving} className="mt-6 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </div>
            )}

            {activeTab === 'security' && (
              <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-100 dark:border-slate-700 p-6 shadow">
                <h2 className="text-xl font-semibold mb-6 dark:text-white">Security</h2>
                <form onSubmit={handleChangePassword} className="space-y-4 mb-8">
                  <input type="password" placeholder="Current Password" value={passwordData.current_password} onChange={(e) => setPasswordData(prev => ({ ...prev, current_password: e.target.value }))} className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-slate-700 dark:text-white rounded-lg" required />
                  <input type="password" placeholder="New Password" value={passwordData.new_password} onChange={(e) => setPasswordData(prev => ({ ...prev, new_password: e.target.value }))} className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-slate-700 dark:text-white rounded-lg" required />
                  <input type="password" placeholder="Confirm Password" value={passwordData.confirm_password} onChange={(e) => setPasswordData(prev => ({ ...prev, confirm_password: e.target.value }))} className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-slate-700 dark:text-white rounded-lg" required />
                  <button type="submit" disabled={changingPassword} className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
                    {changingPassword ? 'Changing...' : 'Change Password'}
                  </button>
                </form>
                <button onClick={() => setShowDeleteModal(true)} className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">
                  Delete Account
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-slate-800 rounded-lg max-w-md w-full p-6">
            <h3 className="text-lg font-semibold mb-4 dark:text-white">Delete Account</h3>
            <input type="password" placeholder="Password" value={deletePassword} onChange={(e) => setDeletePassword(e.target.value)} className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-slate-700 dark:text-white rounded-lg mb-4" />
            <input type="text" placeholder="Type DELETE" value={deleteConfirmation} onChange={(e) => setDeleteConfirmation(e.target.value)} className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-slate-700 dark:text-white rounded-lg mb-4" />
            <div className="flex gap-3">
              <button onClick={() => setShowDeleteModal(false)} className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600">Cancel</button>
              <button onClick={handleDeleteAccount} disabled={deleting || deleteConfirmation !== 'DELETE'} className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;
