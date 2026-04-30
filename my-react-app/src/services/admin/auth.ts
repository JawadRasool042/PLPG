import { adminApi, setAdminTokens, clearAdminTokens, ADMIN_REFRESH_TOKEN_KEY, ADMIN_ACCESS_TOKEN_KEY } from './client';
import type { AdminProfile, LoginResponse } from './types';

export const adminLogin = async (email: string, password: string): Promise<LoginResponse> => {
  const { data } = await adminApi.post<LoginResponse>('/auth/login', { email, password });
  setAdminTokens(data.data.accessToken, data.data.refreshToken);
  return data;
};

export const adminRefreshToken = async (): Promise<string | null> => {
  const refreshToken = localStorage.getItem(ADMIN_REFRESH_TOKEN_KEY);
  if (!refreshToken) return null;

  try {
    const { data } = await adminApi.post<{ success: boolean; data: { accessToken: string } }>('/auth/refresh-token', {
      refreshToken,
    });
    setAdminTokens(data.data.accessToken);
    return data.data.accessToken;
  } catch (error) {
    clearAdminTokens();
    return null;
  }
};

export const adminLogout = async () => {
  try {
    await adminApi.post('/auth/logout');
  } catch (_) {
    // ignore
  }
  clearAdminTokens();
};

export const getAdminProfile = async (): Promise<AdminProfile> => {
  const { data } = await adminApi.get<{ data: AdminProfile }>('/auth/profile');
  return data.data;
};

export const createAdmin = async (payload: { name: string; email: string; password: string; roleId: string }) => {
  const { data } = await adminApi.post('/auth/create-admin', payload);
  return data;
};

export const getStoredAdminTokens = () => ({
  accessToken: localStorage.getItem(ADMIN_ACCESS_TOKEN_KEY),
  refreshToken: localStorage.getItem(ADMIN_REFRESH_TOKEN_KEY),
});
