import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { adminLogin, adminLogout, getAdminProfile } from '../services/admin/auth';
import type { AdminProfile } from '../services/admin/types';
import { clearAdminTokens, getAdminAccessToken } from '../services/admin/client';

interface AdminState {
  admin: AdminProfile | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  fetchProfile: () => Promise<void>;
}

export const useAdminStore = create<AdminState>()(
  persist(
    (set) => ({
      admin: null,
      isAuthenticated: false,
      loading: false,
      error: null,

      login: async (email, password) => {
        try {
          set({ loading: true, error: null });
          const res = await adminLogin(email, password);
          set({ admin: res.data.admin, isAuthenticated: true, loading: false });
          return true;
        } catch (error: any) {
          set({ error: error?.response?.data?.message || 'Login failed', loading: false, isAuthenticated: false });
          clearAdminTokens();
          return false;
        }
      },

      logout: async () => {
        await adminLogout();
        set({ admin: null, isAuthenticated: false, loading: false, error: null });
      },

      fetchProfile: async () => {
        try {
          set({ loading: true });
          const token = getAdminAccessToken();
          if (!token) {
            set({ admin: null, isAuthenticated: false, loading: false });
            return;
          }
          const profile = await getAdminProfile();
          set({ admin: profile, isAuthenticated: true, loading: false });
        } catch (error) {
          set({ admin: null, isAuthenticated: false, loading: false });
          clearAdminTokens();
        }
      },
    }),
    {
      name: 'plpg-admin-auth',
      partialize: (state) => ({
        admin: state.admin,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
